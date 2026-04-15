---
phase: 04-llm-mechanic-generation
plan: 02
subsystem: mechanic-framework
tags: [validation, ast, cli, registry, mech-04, gap-eng16]
requires:
  - 04-01 (flat mechanic layout + load_mechanic_classes API)
  - src/token_world/mechanic/{protocol,loader,registry,context}.py
  - src/token_world/graph (KnowledgeGraph for smoke stage)
provides:
  - src/token_world/mechanic/validation.py (6-stage pipeline)
  - token_world.mechanic.validation.validate(module_path) -> ValidationReport
  - ValidationReport.to_dict() JSON schema (for 04-03 diagnostics sink)
  - MechanicRegistry.scan() returning list[ValidationReport]; invalid modules
    excluded from the index
  - MechanicRegistry.last_scan_reports property (for 04-03)
  - validate-mechanic CLI (human + json formats; exit codes 0/1/2)
affects:
  - src/token_world/mechanic/registry.py (scan return type, validation wiring)
  - src/token_world/cli.py (validate-mechanic command)
  - tests/test_mechanic/test_registry.py (2 new validation-wiring tests)
  - tests/test_mechanic/test_validation.py (21 new tests, created)
  - tests/test_cli/test_validate_mechanic.py (5 new tests, created)
  - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md (rows T1-T4)
  - .planning/phases/04-llm-mechanic-generation/deferred-items.md (created)
tech-stack:
  added: []
  patterns:
    - "6-stage accumulate-within-stage / stop-at-first-hard-fail pipeline (D-13)"
    - "AST walker enforces D-14 rules BEFORE importlib exec (defense-in-depth)"
    - "pytest-as-subprocess with argv list (T-04-TEST-EXEC mitigation: never shell=True)"
    - "dual-layout test-path resolver: probes both project-seed (tests/test_mechanic/test_seeds) and universe-local (<universe>/tests/test_mechanics) locations"
key-files:
  created:
    - src/token_world/mechanic/validation.py
    - tests/test_mechanic/test_validation.py
    - tests/test_cli/test_validate_mechanic.py
    - .planning/phases/04-llm-mechanic-generation/deferred-items.md
  modified:
    - src/token_world/mechanic/registry.py (scan wiring + last_scan_reports)
    - src/token_world/cli.py (validate-mechanic command)
    - tests/test_mechanic/test_registry.py (TestValidationWiring class)
    - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md (T1-T4 rows)
decisions:
  - D-12/D-13 single-entry validate() with 6 stages; hard-fail stops the
    pipeline but findings accumulate within a stage.
  - D-14 AST visitor flags bare-name calls only (per T-04-FORBIDDEN-ATTR-CALL);
    attribute calls like foo.eval() intentionally allowed.
  - D-15 registry auto-scan excludes invalid modules from the live index;
    last_scan_reports property exposes all reports for 04-03 diagnostics.
  - Test-path resolution probes two layouts (project-seed and universe); first
    existing path wins. Accepting both lets the same validate() work for
    src/token_world/mechanic/seeds/*.py and <universe>/mechanics/*.py.
  - Smoke stage builds a minimal KnowledgeGraph() with two claimable nodes.
    CheckResult(passed=False) is explicitly NOT a failure -- only raised
    exceptions fail the stage.
metrics:
  duration: ~45 min
  completed: 2026-04-12
---

# Phase 4 Plan 02: Validation pipeline + validate-mechanic CLI + registry auto-scan — Summary

MECH-04 delivered end-to-end: a single `validate(module_path)` entry running
a 6-stage pipeline (syntax -> ast -> import -> contract -> tests -> smoke),
wired into both `MechanicRegistry.scan()` (auto-scan per D-15) and the new
`token-world validate-mechanic` CLI (fast operator feedback without running a
tick). AST rules from D-14 enforced with file/line/col locations.

## What Changed

### Validation module (Task 1)

- `src/token_world/mechanic/validation.py` (~500 LOC after format)
  - `ValidationFinding` dataclass: `stage`, `rule`, `severity`, `message`,
    `path`, `line`, `col`. All fields JSON-friendly.
  - `ValidationReport` dataclass: `module_path`, `findings`, `passed`, plus
    `add(finding)` helper that flips `passed` on error severity, and
    `to_dict()` returning the stable schema consumed by 04-03.
  - `FORBIDDEN_CALL_NAMES = frozenset({"eval","exec","__import__","compile","globals","open"})`
  - `FORBIDDEN_IMPORT_PREFIXES = ("networkx", "token_world.graph.knowledge_graph")`
  - `_MechanicAstVisitor` overrides `visit_Import`, `visit_ImportFrom`,
    `visit_Call`, `visit_ClassDef`. `visit_Call` only flags `ast.Name` (bare
    names); `ast.Attribute` access passes through. `visit_ClassDef` collects
    classes whose bases include a name or attribute named `"Mechanic"` --
    transitive chains surface at the contract stage (Pitfall 1).
  - Six `_stage_*` functions. Each mutates the shared report. `validate()`
    composes them and short-circuits after any stage that flips `passed`.
  - `_candidate_test_paths` probes both the universe layout
    (`<universe>/tests/test_mechanics/test_<id>.py`) and the project-seed
    layout (walks up from `mechanics/seeds/<id>.py` looking for a sibling
    `tests/test_mechanic/test_seeds/test_<id>.py`). First that exists wins.
  - `_stage_tests` invokes pytest via `subprocess.run([sys.executable, "-m",
    "pytest", ...])` -- argv list, NEVER `shell=True` (T-04-TEST-EXEC
    mitigation verifiable by grep).
  - `_stage_smoke` constructs a fresh `KnowledgeGraph()` in-memory with
    `_smoke_actor` (agent) + `_smoke_target` (entity) nodes, builds a
    `MechanicContext`, and calls `check(ctx)`. Raised exceptions fail;
    `CheckResult(passed=False)` is valid refusal, not failure.

### Tests (Task 2)

- `tests/test_mechanic/test_validation.py` -- 21 tests covering:
  - Happy-path + schema assertions on constants and `to_dict()`.
  - Syntax stage: unparseable source fails with line/col; pipeline halts
    before AST.
  - AST forbidden imports: `import networkx`, `from networkx.utils import X`,
    `from token_world.graph.knowledge_graph import Y`.
  - AST forbidden calls: bare `eval`, both `exec` + `open` accumulated,
    `foo.eval()` attribute call intentionally allowed.
  - AST `no_mechanic_subclass` warning + contract `no_mechanic_subclass` error
    both emitted for modules without a Mechanic subclass.
  - Import stage: `from token_world.nonexistent import Foo` fails at stage
    "import" with rule "import_failed".
  - Contract stage: missing `id`, missing `description`, wrong `check`
    signature `(self, actor, target)`.
  - Tests stage: warning when no sibling test file; failure when pytest
    returns non-zero; pass when sibling test passes.
  - Smoke stage: runtime `RuntimeError` in `check()` fails;
    `CheckResult(passed=False)` passes.

### Registry + CLI + registry tests (Task 3)

- `MechanicRegistry.scan()` now:
  - Returns `list[ValidationReport]` (non-breaking -- existing `__init__`
    caller that discards the value still works; duplicate-id detection
    still active on valid modules).
  - Runs `validate()` on every discovered module BEFORE calling
    `load_mechanic_classes`; failed modules are excluded from the index.
  - Caches the report list under `self._last_scan_reports` exposed via the
    `last_scan_reports` property for 04-03's diagnostics sink.
- `cli.py` gains `@cli.command("validate-mechanic")`:
  - `token-world validate-mechanic <path.py>` (direct-path mode).
  - `token-world validate-mechanic <universe-slug> <mechanic-id>`
    (universe-resolution mode via `UniverseManager`).
  - `--format human` (default): `PASS/FAIL <path>` header then one line per
    finding `[severity] [stage:rule] <path>:<line>:<col> -- <message>`.
  - `--format json`: pretty-printed `ValidationReport.to_dict()`.
  - Exit codes: 0 pass, 1 fail, 2 resolver error (missing slug / missing
    mechanic-id / missing file).
- `tests/test_cli/test_validate_mechanic.py` -- 5 CliRunner tests (seed
  validation, forbidden_import, json format, missing-id error, exit-code
  contract).
- `tests/test_mechanic/test_registry.py` -- gained `TestValidationWiring`
  class with 2 tests (scan returns reports; invalid modules excluded).

### Phase gate + VALIDATION map (Task 4)

- Full suite: 364 passed (was 336; +28 for 04-02: 21 + 5 + 2).
- `ruff check src/` clean. `ruff format --check src/` clean.
- `mypy src/token_world/mechanic/` clean (after adjusting `list[type]` to
  `list[type[Mechanic]]` for `cls.id` access).
- `04-VALIDATION.md` Per-Task Verification Map gained rows 04-02-T1..T4.

## Commits

| Task | Commit | Type | Summary |
|------|--------|------|---------|
| T1   | c3ed4f0 | feat | add validation pipeline (syntax/ast/import/contract/tests/smoke) |
| T2   | b7444f3 | test | comprehensive per-stage + per-AST-rule validation tests |
| T3   | d7df17c | feat | wire validation into registry.scan() + add validate-mechanic CLI |
| T4   | a6c1491 | chore | phase-gate (full suite + mypy) + VALIDATION.md map rows T1-T4 |

## Divergences from RESEARCH.md / PLAN

- **Test-path resolution strategy.** The plan left the exact resolver to
  executor judgement. The executor probes BOTH the universe layout
  (`<universe>/tests/test_mechanics/test_<id>.py`) AND the project-seed layout
  (walks ancestors searching for `tests/test_mechanic/test_seeds/test_<id>.py`).
  Universe layout is checked first (flat Path construction); seed layout
  requires an upward walk with a 6-ancestor cap. Both are probed so the same
  `validate()` works uniformly for scaffolded universes AND `src/.../seeds/`.
- **`_stage_contract` robustness on transitive Mechanic subclasses.** Plan
  D-14 "at least one class subclasses Mechanic directly or transitively".
  The AST stage only detects *direct* inheritance (base is literally named
  `Mechanic`); transitive chains pass the AST warning as usual and are
  caught properly at the runtime contract stage via
  `issubclass(c, Mechanic)`. This matches RESEARCH.md Pitfall 1 and is
  documented in the AST warning's message.
- **Smoke stage minimal fixture.** Plan suggested `KnowledgeGraph(db_path=None)`;
  the actual `KnowledgeGraph.__init__` already defaults `db_path=None`, so
  we use the positional form `KnowledgeGraph()` for clarity.
- **AST visitor class-name matching.** The visitor accepts both
  `class Foo(Mechanic): ...` and `class Foo(module.Mechanic): ...`
  (`ast.Attribute` form with `attr == "Mechanic"`). This follows
  RESEARCH.md Pattern 2 and is a nicety over the plan's bare-name-only
  suggestion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] mypy list[type] doesn't know `cls.id`**
- **Found during:** Task 4 (mypy phase gate).
- **Issue:** `cls.id` accessed in `_stage_tests` and `_stage_smoke` tripped
  `"type" has no attribute "id"` because parameter `mechanic_classes: list[type]`
  erased the `Mechanic` bound.
- **Fix:** Added `TYPE_CHECKING` import of `Mechanic` and changed annotations
  from `list[type]` to `list[type[Mechanic]]` in three places (parameter of
  `_stage_tests`, parameter of `_stage_smoke`, return type and local variable
  of `_stage_contract`).
- **Files modified:** `src/token_world/mechanic/validation.py`
- **Commit:** a6c1491

## Deferred Issues

Logged in `.planning/phases/04-llm-mechanic-generation/deferred-items.md`:

- **Ruff format drift in three 04-01 test files.** `ruff format --check tests/`
  reports diffs for `tests/test_design_validation/test_use_case_schema.py`,
  `tests/test_mechanic/test_loader.py`, and
  `tests/test_universe/test_scaffold.py`. Out of scope per CLAUDE.md §4
  scope boundary; 04-02 phase-gate only requires `ruff format --check src/`
  which is clean. A future plan (04-12 cleanup) can run
  `ruff format tests/` and commit the result.

## Notes for Downstream Plans

- **`ValidationReport.to_dict()` schema is the contract for 04-03.** Keys:
  `module_path: str`, `passed: bool`, `findings: list[dict]`. Each finding
  dict has `stage`, `rule`, `severity`, `message`, `path`, `line`, `col`.
  `DiagnosticsSink.open_validation(mechanic_id)` should consume this dict
  directly (json.dumps it into `validation/<ts>_<id>/report.json`).
- **`MechanicRegistry.last_scan_reports` is the sink's input hook.** After
  every `resume_tick` triggers `registry.scan()`, the reports are available
  without re-calling `validate()`. 04-03's wiring can simply iterate
  `registry.last_scan_reports` and write any `not report.passed` entries
  to the diagnostics sink.
- **CLI shipped with 3-argument shape.** `validate-mechanic [--format human|json]
  UNIVERSE-OR-PATH [MECHANIC-ID]`. 04-05's authoring guide should document
  both modes and their exit codes. Slug mode requires a mechanic-id; direct
  path mode does not.
- **Subprocess for tests stage uses argv list.** No mechanic ID interpolation
  into a shell string. 04-05's authoring guide's "AST rules are not a
  sandbox" note should also cover this (T-04-TEST-EXEC is accepted +
  documented, not a sandboxing boundary).
- **Pipeline semantics.** Hard-fail stops the pipeline at the end of its
  current stage. All findings produced during that stage are reported before
  bailing. Warnings never flip `passed`. 04-04's integration harness should
  use `report.passed` as the pass/fail signal, not length of findings.
- **Empty mechanics dir is still valid.** `scan()` on a missing or empty
  `mechanics/` returns `[]`; no findings, no error. Clear `_index` + clear
  `_classes` + empty `_last_scan_reports`.

## Self-Check: PASSED

- All 4 per-task commits present in `git log --oneline` (c3ed4f0, b7444f3,
  d7df17c, a6c1491).
- All created files exist:
  - `src/token_world/mechanic/validation.py` ✓
  - `tests/test_mechanic/test_validation.py` ✓
  - `tests/test_cli/test_validate_mechanic.py` ✓
  - `.planning/phases/04-llm-mechanic-generation/deferred-items.md` ✓
- Modified files:
  - `src/token_world/mechanic/registry.py` -- `last_scan_reports` property + scan returns reports ✓
  - `src/token_world/cli.py` -- `validate-mechanic` command + `click.Choice(["human", "json"])` ✓
  - `tests/test_mechanic/test_registry.py` -- `TestValidationWiring` class with 2 tests ✓
  - `.planning/phases/04-llm-mechanic-generation/04-VALIDATION.md` -- rows 04-02-T1..T4 ✓
- Phase gates:
  - `uv run pytest -x -q` -> 364 passed ✓
  - `uv run ruff check src/` -> clean ✓
  - `uv run ruff format --check src/` -> clean ✓
  - `uv run mypy src/token_world/mechanic/` -> Success, no issues ✓
  - `grep -n "shell=True" src/token_world/mechanic/validation.py` -> 0 matches ✓
  - `uv run token-world validate-mechanic src/token_world/mechanic/seeds/movement.py` -> PASS ✓
