---
phase: 05-simulation-engine
plan: "03"
title: "Decider + RefusalTemplate + ctx.refuse helper"
subsystem: engine
tags:
  - engine
  - decider
  - refusal
  - mechanic-context
  - d12
  - d13
dependency_graph:
  requires:
    - "05-01 (ClassifierVerdict, MatchResult, Decision Pydantic models)"
    - "05-02 (MatchedResult, NoMatchResult shapes)"
    - "04-mechanic-framework (MechanicContext, CheckResult)"
  provides:
    - "token_world.engine.refusal.RefusalTemplate — 8-code narrative template"
    - "token_world.engine.decider.decide(verdict, match_result) → Decision (D-12)"
    - "MechanicContext.refuse(reason_code, details) → CheckResult (D-13)"
  affects:
    - "05-08 Engine Orchestrator (wires decide() into pipeline)"
    - "All mechanics using check() — can now call ctx.refuse() for consistent narrative"
tech_stack:
  added: []
  patterns:
    - "_SafeDict for missing-key safe-substitution in str.format_map"
    - "TYPE_CHECKING block for CheckResult return type to avoid runtime cycle"
    - "Lazy import pattern: RefusalTemplate imported inside refuse() method body"
    - "Precedence ladder with isinstance dispatch (no match/case for Python 3.9 compat)"
key_files:
  created:
    - src/token_world/engine/refusal.py
    - src/token_world/engine/decider.py
    - tests/test_engine/test_refusal.py
    - tests/test_engine/test_decider.py
    - tests/test_mechanic/test_context_refuse.py
  modified:
    - src/token_world/mechanic/context.py (added refuse() method + CheckResult TYPE_CHECKING import)
    - tests/test_mechanic/test_context_api.py (added refuse to EXPECTED_CALLABLES frozen surface)
decisions:
  - "CheckResult uses reasons: list[str] field (not narrative: str) — adapted refuse() to return CheckResult(passed=False, reasons=[narrative]) to match actual protocol.py definition"
  - "TYPE_CHECKING import for CheckResult return type annotation — avoids runtime cycle while satisfying ruff F821 and providing mypy type safety"
  - "Lazy import of RefusalTemplate inside refuse() method body — avoids engine->mechanic->engine circular dependency at module load time"
metrics:
  duration_minutes: 6
  tasks_completed: 3
  tasks_total: 3
  files_created: 5
  files_modified: 2
  tests_added: 35
  completed_date: "2026-04-13"
---

# Phase 5 Plan 03: Decider + RefusalTemplate + ctx.refuse Summary

Unified refusal surface across all three refusal sources (classifier, conservation, mechanic-level) plus the D-12 precedence-ladder decider that routes classifier verdict + match result to a typed Decision.

## One-liner

RefusalTemplate with 8 reason-code templates, decide() precedence ladder (classifier short-circuits → execute → yield), and ctx.refuse() helper that lets mechanics produce consistent CheckResult refusals via the same template.

## What Was Built

### Task 1: RefusalTemplate (af48c3d)

Created `src/token_world/engine/refusal.py`:

- `_TEMPLATES` dict with 8 known reason codes: `no_viable_action`, `no_such_target`, `low_confidence`, `mechanic_check_failed`, `conservation_violation`, `inventory_full`, `locked`, `blocked`
- `_FALLBACK_TEMPLATE` for unknown codes — interpolates `reason_code` into the narrative
- `RefusalTemplate.render(reason_code, details)` — static method using `_SafeDict` for missing-key safe-substitution (missing keys render as `[key]` rather than raising `KeyError`)
- All narratives are short (≤ 200 chars), grounded, second-person

16 tests in `tests/test_engine/test_refusal.py` covering all known codes, safe substitution, and unknown code fallback.

### Task 2: Decider (aa072f8)

Created `src/token_world/engine/decider.py`:

- `decide(verdict, match_result, *, action_text="") -> Decision`
- Ladder rung 1: `VerdictNoViableAction` / `VerdictNoSuchTarget` / `VerdictLowConfidence` → `RefuseDecision` (short-circuits regardless of match_result)
- Ladder rung 2: `VerdictOk` + `MatchedResult` → `ExecuteDecision(mechanic_id)`
- Ladder rung 3: `VerdictOk` + `NoMatchResult` → `YieldDecision(classified, candidates)`
- `ValueError` when `VerdictOk` received without `match_result`
- `action_text` propagates into `RefuseDecision.details` for narrative rendering

11 tests in `tests/test_engine/test_decider.py`. mypy: zero errors.

### Task 3: MechanicContext.refuse helper (a0ae6a9)

Extended `src/token_world/mechanic/context.py` additively:

- Added `CheckResult` to `TYPE_CHECKING` block for return type annotation (no runtime cost)
- Added `refuse(reason_code, details=None) -> CheckResult` method at the end of the class
- Lazy-imports `RefusalTemplate` and `CheckResult` inside the method body — the `engine→mechanic→engine` cycle is broken because the import happens only at call time, not at module load
- Returns `CheckResult(passed=False, reasons=[narrative])` using the actual `reasons: list[str]` field from `protocol.py`

Updated `tests/test_mechanic/test_context_api.py`: added `refuse` to `EXPECTED_CALLABLES` frozen surface.

8 tests in `tests/test_mechanic/test_context_refuse.py` covering CheckResult shape, determinism, fallback for unknown codes, and lazy-import discipline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CheckResult uses reasons: list[str], not narrative: str**
- **Found during:** Task 3 — plan pseudocode used `CheckResult(passed=False, narrative=narrative)` but `protocol.py` defines `CheckResult(passed: bool, reasons: list[str])`
- **Issue:** Plan's interface block said `narrative: str = ""` but the actual frozen dataclass has `reasons: list[str] = field(default_factory=list)`
- **Fix:** `refuse()` returns `CheckResult(passed=False, reasons=[narrative])` — narrative placed as the first element of the list, which is the natural access pattern for callers
- **Files modified:** `src/token_world/mechanic/context.py`, `tests/test_mechanic/test_context_refuse.py`
- **Commit:** a0ae6a9

**2. [Rule 3 - Blocking issue] ruff F821 on CheckResult return annotation**
- **Found during:** Task 3 lint pass — `refuse() -> "CheckResult"` caused `F821 Undefined name` because `CheckResult` is only lazily imported inside the method body
- **Fix:** Added `from token_world.mechanic.protocol import CheckResult` under `TYPE_CHECKING` block. Since `context.py` has `from __future__ import annotations`, this is zero runtime cost while satisfying both ruff and mypy
- **Files modified:** `src/token_world/mechanic/context.py`
- **Commit:** a0ae6a9 (bundled with Task 3)

## Known Stubs

None. All functionality is fully wired.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or trust boundary schema changes introduced.

## Self-Check: PASSED

All key files exist. All 3 task commits found in git log. 35 new tests pass. Full suite: 1073 passed, 14 skipped, 0 failures.
