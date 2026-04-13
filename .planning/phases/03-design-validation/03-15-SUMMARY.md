---
phase: 03-design-validation
plan: 15
subsystem: validation
tags: [gap-closure, schema, use-cases, validation, uat]

requires:
  - phase: 03-design-validation
    provides: "use-case schema validator (validate_frontmatter) + 35 authored UC fixtures"

provides:
  - "VALID_ASSERTION_KINDS frozenset: closed 6-kind graph_assertion vocabulary"
  - "validate_frontmatter now rejects unknown assertion kinds at load time"
  - "17 new regression tests (parametrized across valid + invalid kinds, plus location-placement defense-in-depth)"
  - "Library sweep test asserting every authored UC uses only whitelisted kinds"

affects: [04-llm-mechanic-generation, 04.1-operator-agent-harness]

tech-stack:
  added: []
  patterns:
    - "Closed vocabulary enforced at the loader boundary (edge validation) rather than deep in downstream consumers"
    - "Defense-in-depth: iterate every plausible container location (expected_observations, setup, actions) so the check survives future UC-schema refactors"
    - "Single-source-of-truth re-export from package __init__ so downstream harnesses import the same constant the validator enforces"

key-files:
  created: []
  modified:
    - "src/token_world/use_cases/loader.py"
    - "src/token_world/use_cases/__init__.py"
    - "tests/test_design_validation/test_use_case_loader.py"
    - "tests/test_design_validation/test_use_case_schema.py"
    - ".planning/phases/03-design-validation/deferred-items.md"

key-decisions:
  - "Enforce the 6-kind whitelist at the validator boundary (cheapest checkpoint); Phase 04 harness can still assert defensively but the first line of defense is load-time rejection"
  - "Defense-in-depth: also iterate setup.graph_assertions and actions[*].graph_assertions even though no current UC uses those locations — UAT report mentioned them and the cost is one extra for-loop"
  - "Re-export VALID_ASSERTION_KINDS from token_world.use_cases so Phase 04 harness imports the single source of truth rather than duplicating the list"

patterns-established:
  - "Whitelist-at-the-edge: fix schema-rot gaps in the validator, not in every downstream consumer"
  - "Parametrized valid + invalid pairing: one parametrized test per vocabulary member confirms the whitelist is symmetric (everything in passes, everything out fails)"

requirements-completed:
  - DVAL-01
  - DVAL-02

duration: 3min
completed: 2026-04-13
---

# Phase 03 Plan 15: Assertion Kind Whitelist Gap Closure Summary

**`validate_frontmatter` now enforces the fixed 6-kind `graph_assertion` vocabulary (`has_node`, `has_edge`, `has_property`, `property_equals`, `not_has_edge`, `not_has_property`) at load time — closes UAT Test 8 schema-rot gap before Phase 04 harness consumes these UCs as integration fixtures.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-13T02:41:35Z
- **Completed:** 2026-04-13T02:44:54Z
- **Tasks:** 3 (2 committed + 1 live probe)
- **Files modified:** 5 (2 src + 2 tests + 1 deferred-items log)

## Accomplishments

- `VALID_ASSERTION_KINDS = frozenset({…})` added to `loader.py` and re-exported from the package public API
- `validate_frontmatter` iterates `expected_observations[*].graph_assertions`, `setup.graph_assertions`, and `actions[*].graph_assertions`, rejecting any assertion whose `kind` is not in the whitelist
- 17 new regression tests: 6 valid-kinds parametrized + 6 invalid-kinds parametrized + 5 scalar (exact-membership contract, setup/actions location coverage, missing-kind rejection, library sweep)
- Live adversarial probe reproduced the exact independent-agent UAT finding: injected `kind: totally_fake_kind` into UC-S01 → validator now catches it; restored cleanly with no diff

## Task Commits

1. **Task 15.1: Add VALID_ASSERTION_KINDS constant + iterate assertion kinds** — `867f44e` (feat)
2. **Task 15.2: Failing-then-passing regression tests for the whitelist** — `e8228f3` (test)
3. **Task 15.3: Live adversarial probe (inject bad kind into UC-S01 on disk)** — not committed; shell-only verification per plan, confirmed PASS with restore-clean diff

## Files Created/Modified

- `src/token_world/use_cases/loader.py` — added `VALID_ASSERTION_KINDS` frozenset and the `_check_assertions` closure that iterates all three plausible container locations
- `src/token_world/use_cases/__init__.py` — re-export `VALID_ASSERTION_KINDS` from the package public API
- `tests/test_design_validation/test_use_case_loader.py` — 11 new tests (1 membership contract, 6 parametrized valid, 6 parametrized invalid, 3 scalar defense-in-depth / missing-kind tests — note one parametrized function serves multiple parametrize cases)
- `tests/test_design_validation/test_use_case_schema.py` — 1 new sweep test `test_every_authored_assertion_uses_a_valid_kind`
- `.planning/phases/03-design-validation/deferred-items.md` — appended `test_registry.py:3` I001 to the pre-existing ruff-errors list (same scope as previously-documented test_mechanic/ issues)

## Decisions Made

- **Enforce at the validator boundary.** Cheapest checkpoint; Phase 04 harness can still add defensive `assert kind in VALID_ASSERTION_KINDS`, but the loader now catches drift before any downstream code sees it.
- **Defense-in-depth location coverage.** UAT's `missing` field named "setup.graph_assertions and action.graph_assertions" even though the real UCs nest under `expected_observations[*].graph_assertions`. The fix iterates all three locations so a future UC-schema refactor that moves assertions doesn't silently re-open the gap.
- **Single-source-of-truth re-export.** `VALID_ASSERTION_KINDS` is re-exported from `token_world.use_cases.__init__`, so Phase 04 harness imports the same constant the validator enforces — no drift between the two sets.

## Deviations from Plan

None — plan executed exactly as written. All three tasks' acceptance criteria met without auto-fixes or architectural changes. The pre-commit hooks reformatted whitespace/imports on both commits, which is routine and not a deviation.

## Issues Encountered

**Pre-existing ruff errors in `tests/test_mechanic/` (out of scope):** `uv run ruff check src/ tests/` exits non-zero with 4 errors, all in `tests/test_mechanic/*.py`. Reproduced against `HEAD~2` → pre-existing, same issues already documented in `deferred-items.md` from Plan 03-14. One new row added (`test_registry.py:3` I001). Not fixed per the SCOPE BOUNDARY rule; `uv run ruff check src/` and `uv run ruff check tests/test_design_validation/` both pass clean.

## User Setup Required

None — no external service configuration required.

## Verification Evidence

- `uv run pytest tests/test_design_validation/ -v` → 27 passed (baseline 10, +17 new)
- `uv run pytest tests/ -q` → 316 passed (no regression elsewhere)
- `uv run ruff check src/token_world/use_cases/` → All checks passed
- `uv run mypy src/token_world/` → Success: no issues found in 39 source files
- Live probe printed: `PASS — validator rejected totally_fake_kind: [".planning/use-cases/spatial/UC-S01-movement-through-doorway.md: expected_observations[0].graph_assertions[0].kind 'totally_fake_kind' not in ['has_edge', 'has_node', 'has_property', 'not_has_edge', 'not_has_property', 'property_equals']"]`
- Restore: `git diff .planning/use-cases/spatial/UC-S01-movement-through-doorway.md` returns empty

## Next Phase Readiness

- UAT Test 8 (severity: major) flips from `issue` to `pass`
- Phase 04 mechanic-authoring pipeline can now safely import `VALID_ASSERTION_KINDS` from `token_world.use_cases` and rely on it as the canonical kind vocabulary
- Phase 04.1 operator agent harness can trust that any UC passing `validate_frontmatter` will never surface an unexpected `kind` at runtime

## Self-Check: PASSED

- `src/token_world/use_cases/loader.py` — FOUND (contains `VALID_ASSERTION_KINDS`)
- `src/token_world/use_cases/__init__.py` — FOUND (re-exports `VALID_ASSERTION_KINDS`)
- `tests/test_design_validation/test_use_case_loader.py` — FOUND (contains `totally_fake_kind` and the 6 required test-function names)
- `tests/test_design_validation/test_use_case_schema.py` — FOUND (contains `test_every_authored_assertion_uses_a_valid_kind`)
- Commit `867f44e` — FOUND in `git log`
- Commit `e8228f3` — FOUND in `git log`

---
*Phase: 03-design-validation*
*Completed: 2026-04-13*
