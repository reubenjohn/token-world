---
phase: 05-simulation-engine
plan: "01"
title: "Core scaffolding: engine subpackage + classifier + RNG + config"
subsystem: engine
tags:
  - engine
  - classifier
  - rng
  - config
  - scaffolding
  - pydantic
dependency_graph:
  requires:
    - "04-mechanic-framework (MechanicContext, validation, seeds)"
    - "04.1-operator-agent-harness (YieldSignal contract)"
  provides:
    - "token_world.engine package with Pydantic models"
    - "EngineConfig loader from universe.yaml"
    - "Haiku Classifier (ClassifierVerdict discriminated union)"
    - "MechanicContext.rng seeded RNG (D-19)"
    - "AST rule: import random forbidden in mechanics"
    - "universe.yaml scaffold with random seed"
    - "tests/test_engine/ package with conftest fixtures"
  affects:
    - "05-02 through 05-06 (all Wave-1 plans gate on this)"
tech_stack:
  added:
    - "pydantic v2 for engine models (Annotated discriminated unions)"
    - "PyYAML for universe.yaml parsing"
    - "hashlib.blake2b for deterministic RNG seeding"
    - "secrets.randbits(63) for universe seed generation"
  patterns:
    - "Annotated[Union[...], Field(discriminator='kind')] for tagged unions"
    - "extra='ignore' on all Pydantic models for Haiku output safety"
    - "Lazy cached property pattern for ctx.rng"
    - "FORBIDDEN_EXACT_IMPORTS frozenset for exact-name AST checks"
key_files:
  created:
    - src/token_world/engine/__init__.py
    - src/token_world/engine/models.py
    - src/token_world/engine/config.py
    - src/token_world/engine/classifier.py
    - src/token_world/universe/templates/universe_yaml.py
    - tests/test_engine/__init__.py
    - tests/test_engine/conftest.py
    - tests/test_engine/test_models.py
    - tests/test_engine/test_config.py
    - tests/test_engine/test_classifier.py
    - tests/test_mechanic/test_context_rng.py
    - tests/test_mechanic/test_validation_ast_rng.py
    - scripts/check_seed_mechanics.py
  modified:
    - src/token_world/mechanic/context.py (added rng property + tick_id/universe_seed kwargs)
    - src/token_world/mechanic/validation.py (added FORBIDDEN_EXACT_IMPORTS + random check)
    - src/token_world/universe/scaffold.py (added universe.yaml seeding)
    - src/token_world/universe/templates/__init__.py (added universe_yaml exports)
    - src/token_world/mechanic/seeds/contagion.py (migrated from import random to ctx.rng)
    - tests/test_mechanic/test_context_api.py (added rng to known_attrs)
decisions:
  - "Used Annotated[Union[...], Field(discriminator='kind')] instead of plain Union for Pydantic v2 discriminated union compatibility"
  - "Used FORBIDDEN_EXACT_IMPORTS frozenset (separate from FORBIDDEN_IMPORT_PREFIXES) to allow random_* prefixed module names while blocking stdlib random"
  - "Migrated contagion.py from GAP-GRAPH05 workaround to ctx.rng with graceful fallback for smoke tests"
metrics:
  duration_minutes: 65
  tasks_completed: 6
  tasks_total: 6
  files_created: 13
  files_modified: 7
  tests_added: 45
  completed_date: "2026-04-13"
---

# Phase 5 Plan 01: Core Scaffolding Summary

Wave-0 foundation for the Phase 5 simulation engine. All six Wave-1 plans (matcher, decider, visibility, observer, conservation, passive sweep) can now proceed in parallel against this scaffolding.

## One-liner

Engine subpackage with Pydantic discriminated-union models, Haiku classifier with retry/threshold/target-check, deterministic ctx.rng via BLAKE2b, EngineConfig from universe.yaml, and AST rule forbidding import random.

## What Was Built

### Task 1: Engine package + Pydantic models (5e4eb31)

Created `src/token_world/engine/` with `__init__.py` and `models.py`.

Models:
- `ClassifiedAction`: verb/actor/target/indirect_object/params (GAP-ENG02)
- `ClassifierVerdict`: discriminated union of VerdictOk/VerdictNoViableAction/VerdictNoSuchTarget/VerdictLowConfidence
- `MatchResult`: discriminated union of MatchedResult/NoMatchResult
- `Decision`: discriminated union of ExecuteDecision/YieldDecision/RefuseDecision
- `TickSummary`: schema v1 for tick JSON files

All models use `extra="ignore"` so Haiku output extras don't crash parsing.

12 unit tests in `tests/test_engine/test_models.py`.

### Task 2: EngineConfig + universe.yaml scaffolding (cf9d35b)

`src/token_world/engine/config.py`:
- `EngineConfig` frozen dataclass with `max_chain_depth=10`, `classifier_min_confidence=0.6`, `universe_seed=0`
- `load_engine_config(path)`: soft-fail (warn + defaults) on missing/malformed YAML
- `generate_universe_seed()`: 63-bit positive integer via `secrets.randbits(63)`

`src/token_world/universe/templates/universe_yaml.py`:
- `UNIVERSE_YAML_TEMPLATE` and `render_universe_yaml(universe_seed=...)` 

`src/token_world/universe/scaffold.py`:
- Added idempotent guard: creates `universe.yaml` only if absent

13 tests across `test_config.py` and `test_scaffold_universe_yaml.py`.

### Task 3: MechanicContext.rng property (049bf5c)

Extended `MechanicContext.__init__` with `tick_id: str | None = None` and `universe_seed: int | None = None` keyword-only args. Added lazy `rng` property:

```python
digest = hashlib.blake2b(f"{self._universe_seed}:{self._tick_id}".encode(), digest_size=8).digest()
seed_int = int.from_bytes(digest, "big")
self._rng = random.Random(seed_int)
```

Raises `RuntimeError` with clear message if either kwarg is missing. Cached on first access. Backwards compatible — existing callers unaffected.

8 tests in `test_context_rng.py`. Zero regressions in existing 494 mechanic tests.

### Task 4: AST rule — forbid import random (cba009c)

Added `FORBIDDEN_EXACT_IMPORTS = frozenset({"random"})` to `validation.py`. Updated `_is_forbidden_import` to check exact set before prefix set.

- `import random` → fails validation (error mentioning "random")
- `from random import choice` → fails
- `import random_extra` → passes (prefix, not exact match)
- `ctx.rng` (attribute access) → passes

Migrated `contagion.py` from `import random` (GAP-GRAPH05 workaround) to `ctx.rng` with graceful fallback for smoke-test contexts.

Added `scripts/check_seed_mechanics.py` as a reusable validation script. All 28 seeds pass.

5 tests in `test_validation_ast_rng.py`.

### Task 5: Haiku Classifier wrapper (b19308d)

`src/token_world/engine/classifier.py`:
- `Classifier` dataclass wrapping raw Anthropic SDK
- Retries once on malformed JSON before returning `VerdictNoViableAction(reason="classifier output malformed after retry")`
- Post-processing: confidence threshold → VerdictLowConfidence; target not in graph → VerdictNoSuchTarget
- Optional `DiagnosticsSink` integration via `tick_diag_ctx` parameter

11 tests in `test_classifier.py` using `MockAnthropicClient`. mypy: zero errors.

### Task 6: Shared test fixtures (029eb96)

`tests/test_engine/conftest.py` provides:
- `MockAnthropicClient` / `_MessagesProxy` (with call recording and usage tracking)
- `mock_anthropic_haiku`: canned classifier-ok response
- `mock_anthropic_sonnet`: canned observer response
- `tmp_universe`: minimal scaffolded universe path
- `kg`: blank in-memory KnowledgeGraph
- `seeded_ctx`: MechanicContext(universe_seed=424242, tick_id="tick_1")

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Migrated contagion.py from import random to ctx.rng**
- **Found during:** Task 4 — running `scripts/check_seed_mechanics.py` after adding the AST rule
- **Issue:** `src/token_world/mechanic/seeds/contagion.py` used `import random` as a documented GAP-GRAPH05 workaround. The new AST rule correctly flagged it.
- **Fix:** Removed `import random` and `_resolve_seed()`. Now uses `ctx.rng` with a fallback for smoke-test contexts (no tick_id/universe_seed): `rate >= 1.0` → certain, `< 1.0` → zero.
- **Files modified:** `src/token_world/mechanic/seeds/contagion.py`
- **Commit:** cba009c (bundled with Task 4)

**2. [Rule 2 - Missing critical functionality] Added scripts/check_seed_mechanics.py**
- **Found during:** Task 4 — needed to validate all seed mechanics after AST rule change
- **Rationale:** The plan's acceptance criteria required verifying all seeds pass. An inline python -c command would be opaque and not reusable. Promoted to a committed script per CLAUDE.md §4.
- **Files created:** `scripts/check_seed_mechanics.py`
- **Commit:** cba009c (bundled with Task 4)

**3. [Rule 2 - Missing critical functionality] Added rng to test_context_api.py frozen surface**
- **Found during:** Task 3 — `test_context_api.py::test_no_unexpected_public_methods` failed because `rng` is a new public property
- **Fix:** Added `"rng"` to the `known_attrs` set in the frozen-surface test
- **Files modified:** `tests/test_mechanic/test_context_api.py`
- **Commit:** 049bf5c (bundled with Task 3)

## Known Stubs

None. All implemented functionality is fully wired.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or trust boundary schema changes introduced. The Classifier makes outbound API calls but this is the intended design (D-04) and was already in the threat model.

## Self-Check: PASSED

All key files exist. All 6 task commits found in git log. 45 tests pass in
`tests/test_engine/ tests/test_mechanic/test_context_rng.py tests/test_mechanic/test_validation_ast_rng.py`.
