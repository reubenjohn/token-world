---
phase: 04-llm-mechanic-generation
plan: 05
subsystem: mechanic-authoring
tags: [docs, cli, scaffold, mech-03, auto-03, d-30, d-31, d-32, d-38]
requires:
  - 04-01 (flat mechanic layout; Mechanic ABC + class-level id/description/voluntary/tags)
  - 04-02 (validate-mechanic CLI — scaffolded skeleton must pass validation)
  - src/token_world/mechanic/{protocol,context,matchers,validation}.py
  - src/token_world/universe/{scaffold,templates/claude_md}.py
  - src/token_world/cli.py
provides:
  - docs/guides/authoring-mechanics.md (665 lines, 15 ## headings)
  - token-world scaffold-mechanic CLI (lowercase-id regex; refuses overwrite; skeleton passes validation)
  - Universe-local docs/authoring-mechanics.md (byte-identical copy via scaffold, D-31)
  - Updated universe CLAUDE.md template enumerating what the universe-local guide covers
  - `blocked_by` class-attribute stub convention documented (required by plan 04-09 MECH09/MECH12)
  - GAP-MECH19 absorbed (trust-boundary rationale obsolete per D-35)
  - GAP-MECH26 absorbed (reactive-cycle authoring guidelines)
  - T-04-AST-BYPASS accepted + disclosed in the guide
  - T-04-SCAFFOLD-ID-TRAVERSAL mitigated via regex gate + test
  - VALIDATION.md rows 04-05-T1..T3
affects:
  - docs/guides/authoring-mechanics.md (created)
  - src/token_world/cli.py (scaffold-mechanic command + skeletons)
  - src/token_world/universe/scaffold.py (_copy_authoring_guide)
  - src/token_world/universe/templates/claude_md.py (Mechanic Authoring pointer expanded)
  - tests/test_cli/test_scaffold_mechanic.py (5 tests, created)
  - tests/test_universe/test_scaffold.py (TestScaffoldAuthoringGuide class, 1 test)
  - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md (rows T1-T3)
  - .planning/phases/04-llm-mechanic-generation/deferred-items.md (continuity note)
tech-stack:
  added: []
  patterns:
    - "CLI regex ^[a-z][a-z0-9_]*$ rejects traversal / mixed-case ids before touching the filesystem (T-04-SCAFFOLD-ID-TRAVERSAL mitigation)"
    - "Compile-green skeleton: pytest.skip placeholder test so scaffolded mechanics never emit a red bar while waiting to be filled in"
    - "Scaffold guide copy via shutil.copy2 from framework-repo docs/guides/ path; silent no-op if source guide missing (partial checkouts)"
    - "Skeleton imports exactly the symbols allowed by D-14 AST rules so freshly scaffolded mechanics pass validation on first invocation"
key-files:
  created:
    - docs/guides/authoring-mechanics.md
    - tests/test_cli/test_scaffold_mechanic.py
  modified:
    - src/token_world/cli.py (scaffold-mechanic command + _MECHANIC_SKELETON + _TEST_SKELETON + _camel_case)
    - src/token_world/universe/scaffold.py (_copy_authoring_guide; wired into scaffold_universe)
    - src/token_world/universe/templates/claude_md.py (Mechanic Authoring pointer expanded)
    - tests/test_universe/test_scaffold.py (TestScaffoldAuthoringGuide class)
    - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md (rows 04-05-T1..T3)
    - .planning/phases/04-llm-mechanic-generation/deferred-items.md (04-05 continuity note)
decisions:
  - Applied D-18 / D-30 literally: the guide IS the prompt; no prompt-assembly pipeline.
  - Applied D-31: scaffold copies docs/guides/authoring-mechanics.md to <universe>/docs/authoring-mechanics.md byte-identical; test asserts byte equality.
  - Applied D-32: scaffold-mechanic emits BOTH a module skeleton AND a pytest.skip test stub (plan's optional-stub question resolved toward "emit both").
  - Applied D-35: no `source`/`reviewed` metadata; the validation gate IS the review step. Guide's §10 absorbs GAP-MECH19.
  - Applied D-38: `blocked_by` class attribute documented as the framework-gap-stub convention. Guide's §8 gives the exact template 04-09 will follow for MECH09 (GAP-ENG03) and MECH12 (GAP-ENG05).
  - Guide length target 500-700; landed at 665.
  - Skeleton format: ``voluntary = {voluntary}`` uses Python's ``{False, True}`` str repr directly — no extra branch for the bool.
metrics:
  duration: ~12 min
  completed: 2026-04-12
---

# Phase 4 Plan 05: Authoring guide + scaffold-mechanic CLI — Summary

Delivers the operator-facing authoring surface that D-17 / D-18 committed
to in lieu of prompt-engineering and retry-plumbing. The 665-line
developer guide is the canonical reference for every mechanic author
from this point forward; the universe-scaffold copies it into every new
universe so operators never leave the universe folder; `scaffold-mechanic`
tightens the authoring loop to one command.

The guide absorbs two "gaps" that become documentation under inversion
of control: GAP-MECH26 (reactive-cycle cautions) and GAP-MECH19 (trust
boundary obsolete per D-35). It also locks in the `blocked_by` class
attribute convention that plan 04-09 needs for MECH09 and MECH12 stubs.

## Guide Table of Contents

`docs/guides/authoring-mechanics.md` ships with 14 numbered sections
(15 `##` headings total, including the preamble-less intro).

| # | Section | Key content |
|---|---------|-------------|
| 1 | Introduction | Universe-as-codebase metaphor; inversion of control (D-01); what Phase 4 provides vs does not |
| 2 | File Layout | Flat `<id>.py`; `_helpers.py` underscore convention; mirrored test tree (D-03..D-06); registry discovery walkthrough |
| 3 | Mechanic Class Contract | Required class attrs (`id`, `description`); defaulted attrs (`voluntary`, `tags`); required methods (`check`, `apply`); optional `watches` |
| 4 | MechanicContext DSL Reference | All query + mutation methods with gotchas; `spatial`/`temporal` lazy indices; node-id claim pattern; JSON-serializable-property reminder |
| 5 | Voluntary vs Involuntary — Matcher Declaration | `PropertyChangeMatcher`, `EdgeMatcher`, `NodeMatcher`; chain-execution and `max_chain_depth=10` |
| 6 | The Validation Gate (D-14) | 6-stage table; forbidden imports + calls + WHY; **T-04-AST-BYPASS "NOT a sandbox" disclaimer**; exit codes 0/1/2 |
| 7 | `_helpers.py` Convention (D-05, D-11) | Free-functions-over-base-classes until ≥3 shared uses; example `_find_open_passage` helper |
| 8 | Framework-Gap-Stub Convention (D-38) | `blocked_by = "<GAP-ID>"` class attr pattern; MUST NOT import absent symbols; `check → passed=False`; `apply → []` |
| 9 | Reactive-Cycle Cautions (GAP-MECH26 absorbed) | Trigger-set vs side-effect-set overlap test; property-transition discrimination; `ExecutionTrace` assertion patterns; idempotence as insurance |
| 10 | Trust Boundary Rationale (GAP-MECH19 absorbed) | Inversion of control = no `source`/`reviewed` fields; validation gate IS the review step (D-35) |
| 11 | Testing Conventions | Mirrored tree; `KnowledgeGraph()` fixture pattern; `ChainExecutionEngine` for multi-mechanic chain tests |
| 12 | Common Anti-Patterns | Direct `kg._graph` access; mutable class containers; `assert` for validation; non-JSON props; hardcoded IDs; blocking IO; re-checking in `apply`; `print` |
| 13 | Worked Examples | Annotated walkthroughs of `movement.py` (voluntary+mutating), `observation.py` (voluntary+read-only), `environmental_reaction.py` (involuntary+matcher-driven) |
| 14 | Workflow | End-to-end: scaffold → edit → validate → iterate → tick → inspect diagnostics → prune |

A final "Reference" section points at the source-of-truth files
(`protocol.py`, `context.py`, `matchers.py`, `validation.py`, seeds,
`cli.py`) and the decision IDs (D-01, D-11, D-17, D-18, D-30, D-31,
D-32, D-35, D-38).

## scaffold-mechanic CLI

### Shape

```
token-world scaffold-mechanic <universe-slug> --id <mechanic-id> \
    [--voluntary | --involuntary] [--description "<one-line>"]
```

### Behavior

| Step | Behavior |
|------|----------|
| Validate `--id` | Regex `^[a-z][a-z0-9_]*$`. Fails exit 2 on mixed-case, hyphens, leading digit, empty — rejects every traversal shape (`..`, `../`, `.`, `/`). |
| Resolve universe | `UniverseManager.load(slug)` — `FileNotFoundError` / `ValueError` → exit 1 with "Error: ...". |
| Refuse overwrite | `mechanics/<id>.py` exists → exit 1 "already exists". `tests/test_mechanics/test_<id>.py` exists → exit 1. |
| Write skeleton | `<universe>/mechanics/<id>.py` with a `<CamelCase>Mechanic` class declaring `id`, `description`, `voluntary`, `tags=[]`, plus TODO-stub `check` / `apply`. |
| Write test stub | `<universe>/tests/test_mechanics/test_<id>.py` with a `@pytest.mark.skip` placeholder. Runs green under pytest (skipped, not failed). |
| Report | Prints "Scaffolded <module-path>" and "Scaffolded <test-path>" on success. |

### Skeleton contract

The emitted skeleton module imports exactly the symbols that the D-14
AST gate permits (`token_world.graph.Mutation`,
`token_world.mechanic.protocol.{CheckResult, Mechanic}`,
`token_world.mechanic.context.MechanicContext` under `TYPE_CHECKING`).
It therefore passes validation on first run — verified by
`test_scaffolded_module_passes_validation` (exit 0, output `PASS`).

### Exit codes

| Code | Meaning |
|------|---------|
| 0    | success |
| 1    | universe not found OR file already exists (refuse-overwrite) |
| 2    | invalid `--id` (regex rejected) |

Consistent with `validate-mechanic` (04-02) and `prune-diagnostics` (04-03).

## `blocked_by` Convention (spec for plan 04-09)

Plan 04-09 (and any other plan that ships a stub for a mechanic blocked
on a framework gap) MUST follow this exact pattern from §8 of the guide:

```python
class <Name>Mechanic(Mechanic):
    """<one-line description> (MECH<NN>; blocked on <GAP-ID>)."""

    id = "<mechanic_id>"
    description = "<one-line description> (blocked on <GAP-ID>)"
    voluntary = <True|False>
    tags: list[str] = [<cluster-tags>]
    blocked_by = "<GAP-ID>"  # e.g. "GAP-ENG03" or "GAP-ENG05"

    def check(self, ctx: "MechanicContext") -> CheckResult:
        return CheckResult(
            passed=False,
            reasons=[f"blocked by framework gap {self.blocked_by}"],
        )

    def apply(self, ctx: "MechanicContext") -> list[Mutation]:
        return []
```

Contract guarantees:

- **No absent-symbol imports.** The module uses only already-shipped
  symbols. Validation stage 3 (import) will pass.
- **Standardized refusal reason.** The string `"blocked by framework
  gap <GAP-ID>"` appears verbatim in `check().reasons` so the
  integration harness can grep it.
- **No-op apply.** Returns `[]`. A stub must never mutate the graph.
- **`blocked_by` class attribute.** Plain string, not a method. The
  integration test harness reads `cls.blocked_by` via `getattr(cls,
  "blocked_by", None)`.
- **Description echoes the gap id.** So `list-mechanics` output makes
  the blocker visible without further drilling.

When the framework gap closes, the stub is rewritten in place: `blocked_by`
is deleted, `check` and `apply` are filled in, and the integration
harness row flips from `blocked_by_framework_gap` to `pass`.

## What plan 04-09 should cite from this guide

Plan 04-09's MECH09 and MECH12 plans should cite:

- **§8 (Framework-Gap-Stub Convention)** — the exact skeleton to reproduce.
  Do not reinvent the blocked-by pattern; copy it.
- **§3 (Mechanic Class Contract)** — required/defaulted attributes; the
  stub's `tags` list must be non-empty so `query_by_tag` still indexes
  the stub.
- **§6 (The Validation Gate)** — remind the author that the stub
  module MUST still pass the full 6-stage pipeline; `blocked_by` is
  not an escape hatch from validation.
- **§9 (Reactive-Cycle Cautions)** — only relevant if the specific
  stub is involuntary. MECH09 (social/belief, GAP-ENG03) is likely
  voluntary; MECH12 (cooperation, GAP-ENG05) is likely voluntary too.

## Test Counts

- **Before plan:** 399 passed.
- **After plan:** 405 passed (+6 = 5 scaffold-mechanic CLI tests + 1
  scaffold-copies-authoring-guide test).

## Lint / Format / Type

- `uv run ruff check` on files touched by this plan
  (`cli.py`, `universe/scaffold.py`, `universe/templates/claude_md.py`):
  clean.
- `uv run ruff format --check` on the same three files: clean (formatter
  applied twice during execution; second run was a no-op).
- `uv run mypy` on the same three files: clean (no issues).
- Full-suite `ruff check src/` still shows the two pre-existing
  E501 lines in `src/token_world/mechanic/validation.py` (documented in
  `deferred-items.md` under 04-03 and 04-05 sections — out of scope).

## Deviations from Plan

### Auto-fixed / in-scope

**1. [Rule 2 - Style] Ruff format drift on newly authored skeleton code.**
- **Found during:** Task 2 phase-gate (`ruff format --check src/`).
- **Issue:** Both the scaffold-mechanic CLI addition to `cli.py` and the
  `_copy_authoring_guide` helper in `scaffold.py` landed in long-form
  layouts that the project's ruff configuration prefers to collapse
  (single-line `click.echo` string instead of implicitly concatenated
  string, single-line `Path / ...` chain instead of multi-line).
- **Fix:** Ran `uv run ruff format src/token_world/cli.py
  src/token_world/universe/scaffold.py`. Two files reformatted, no
  behavioral changes.
- **Commit:** `560c869` (rolled into the Task 2 GREEN commit).

### Pre-existing / out-of-scope (logged to deferred-items.md)

- `src/token_world/mechanic/validation.py` still carries two E501
  findings (lines 441, 544) and a format diff from commit `a6c1491`
  (04-02 Task 4). Unchanged by this plan. Continuity note added under
  "04-05 discoveries" in `deferred-items.md`. 04-12 cleanup will
  address.

## Threat Flags

None introduced beyond the plan's `<threat_model>`:

- **T-04-SCAFFOLD-ID-TRAVERSAL (mitigated):** Regex gate at the start
  of `scaffold_mechanic` rejects any id that isn't
  `lowercase[a-z0-9_]*`. Verifiable via `test_invalid_id_errors` and
  by grepping `\^\[a-z\]` in `cli.py` around `scaffold_mechanic`.
- **T-04-AST-BYPASS (accept + document):** The authoring guide §6
  explicitly states AST rules are "a reasonable-effort pre-runtime
  control, NOT a sandbox." Runtime bypass via dynamic imports is
  acknowledged; snapshots + rollback are the runtime safety net. No
  code-level mitigation in v1.

No new network endpoints, auth paths, schema changes at trust
boundaries, or shell interpolation surface beyond what the plan
anticipated.

## Notes for Downstream Plans

- **Plan 04-06..04-11 (seed mechanic authoring waves):** Use
  `token-world scaffold-mechanic <slug> --id <mech_id>` to bootstrap
  each cluster's files. The emitted skeleton is compile-green AND
  validation-green — authors start from a passing baseline and
  progressively fill in `check`/`apply`.
- **Plan 04-09 (MECH09, MECH12 stubs):** See the spec above (`blocked_by
  Convention`). Copy §8's skeleton verbatim. Grep for the
  standardized refusal string in the integration-harness assertion.
- **Plan 04-12 (final cleanup + RELEASE):** Phase-gate will run
  `ruff format --check src/` on the whole tree; at that point the
  deferred `validation.py` drift needs to be resolved. Either split
  the two long function signatures across lines or add
  `# noqa: E501` with a tagged reason.
- **Authoring guide is under docs/guides/**, not in a universe. The
  universe-local copy is a byte-identical snapshot; updates to the
  framework-repo copy only land in newly-created universes. Existing
  universes can re-pull via `cp docs/guides/authoring-mechanics.md
  <universe>/docs/authoring-mechanics.md` until a future CLI adds a
  "refresh guide" command (not in scope for Phase 4).
- **Scaffold-mechanic emits a `pytest.skip` stub, not an empty file.**
  This is deliberate: running `uv run pytest tests/test_mechanics/`
  in a freshly scaffolded universe never shows a red bar for
  not-yet-implemented mechanics. Authors un-skip as they implement.

## Commits

| Task | Commit  | Type | Summary |
|------|---------|------|---------|
| T1   | 4438fbf | docs | write authoring-mechanics guide (14 sections, 665 lines) |
| T2 (RED)   | 77260d4 | test | add failing tests for scaffold-mechanic CLI + guide copy |
| T2 (GREEN) | 560c869 | feat | scaffold-mechanic CLI + universe guide copy (D-31, D-32) |

## Self-Check: PASSED

- All 3 commits present in `git log --oneline` (4438fbf, 77260d4, 560c869).
- Files created:
  - `docs/guides/authoring-mechanics.md` ✓ (665 lines, 15 `##` headings)
  - `tests/test_cli/test_scaffold_mechanic.py` ✓ (5 tests)
- Files modified:
  - `src/token_world/cli.py` — `scaffold_mechanic` command + `_MECHANIC_SKELETON` + `_TEST_SKELETON` + `_camel_case` ✓
  - `src/token_world/universe/scaffold.py` — `_copy_authoring_guide` helper + wired into `scaffold_universe` ✓
  - `src/token_world/universe/templates/claude_md.py` — `Mechanic Authoring` pointer expanded ✓
  - `tests/test_universe/test_scaffold.py` — `TestScaffoldAuthoringGuide` class with byte-identity assertion ✓
  - `.planning/phases/04-llm-mechanic-generation/04-VALIDATION.md` — rows 04-05-T1..T3 ✓
  - `.planning/phases/04-llm-mechanic-generation/deferred-items.md` — 04-05 continuity note ✓
- Acceptance greps:
  - `wc -l docs/guides/authoring-mechanics.md` → 665 ≥ 400 ✓
  - `grep -c "^## " docs/guides/authoring-mechanics.md` → 15 ≥ 14 ✓
  - `grep -c "NOT a sandbox\|not a sandbox" docs/guides/authoring-mechanics.md` → 3 ≥ 1 ✓
  - `grep -c "blocked_by" docs/guides/authoring-mechanics.md` → 5 ≥ 2 ✓
  - `grep -c "GAP-MECH19\|inversion of control\|source='llm_generated'" docs/guides/authoring-mechanics.md` → 4 ≥ 2 ✓
  - `grep -c "GAP-MECH26\|reactive cycle\|cycle" docs/guides/authoring-mechanics.md` → 6 ≥ 2 ✓
  - `grep -n '@cli.command("scaffold-mechanic")' src/token_world/cli.py` → 1 match ✓
  - `grep -c "_MECHANIC_SKELETON\|_TEST_SKELETON" src/token_world/cli.py` → 4 ≥ 2 ✓
  - `grep -n "authoring-mechanics.md" src/token_world/universe/scaffold.py` → 5 matches ≥ 1 ✓
  - `grep -n "docs/authoring-mechanics.md\|in this universe" src/token_world/universe/templates/claude_md.py` → 1 match ≥ 1 ✓
  - `grep -c "^def test_" tests/test_cli/test_scaffold_mechanic.py` → 5 ≥ 5 ✓
  - `grep -n "def test_scaffold_copies_authoring_guide" tests/test_universe/test_scaffold.py` → 1 match ✓
  - `grep -c "04-05-T" .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md` → 3 ≥ 3 ✓
- Phase gate:
  - `uv run pytest -x -q` → 405 passed ✓
  - `uv run ruff check src/token_world/cli.py src/token_world/universe/scaffold.py src/token_world/universe/templates/claude_md.py` → clean ✓
  - `uv run ruff format --check src/token_world/cli.py src/token_world/universe/scaffold.py src/token_world/universe/templates/claude_md.py` → clean ✓
  - `uv run mypy src/token_world/cli.py src/token_world/universe/scaffold.py src/token_world/universe/templates/claude_md.py` → clean ✓
- CLI smoke (not run automatically — would require an actual created
  universe; exercised instead via `test_scaffolds_module_and_test_files`
  and `test_scaffolded_module_passes_validation`).
