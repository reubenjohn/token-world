---
phase: 04-llm-mechanic-generation
plan: 03
subsystem: mechanic-framework
tags: [diagnostics, filesystem, cli, registry, auto-02, d-15-closure]
requires:
  - 04-01 (flat mechanic layout)
  - 04-02 (validation pipeline — ValidationReport.to_dict() is the sink payload)
  - src/token_world/universe/manager.py (UniverseManager.load for CLI slug resolution)
provides:
  - src/token_world/mechanic/diagnostics.py (DiagnosticsSink + TickDiagnostics)
  - SCHEMA_VERSION = 1 public constant
  - _atomic_write_json helper (module-private, reused by registry wiring)
  - token-world prune-diagnostics CLI (dry-run default)
  - MechanicRegistry.scan(diagnostics_sink=...) kwarg closing D-15
affects:
  - src/token_world/mechanic/__init__.py (public exports: DiagnosticsSink, TickDiagnostics, SCHEMA_VERSION)
  - src/token_world/mechanic/registry.py (scan kwarg + _write_validation_diagnostics helper)
  - src/token_world/cli.py (prune-diagnostics command)
  - tests/test_mechanic/test_diagnostics.py (26 tests, created)
  - tests/test_mechanic/test_registry.py (TestRegistrySinkWiring class, 3 tests)
  - tests/test_cli/test_prune_diagnostics.py (6 tests, created)
  - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md (rows T1-T5)
  - .planning/phases/04-llm-mechanic-generation/deferred-items.md (pre-existing validation.py drift)
tech-stack:
  added: []
  patterns:
    - "Atomic JSON write: tempfile.mkstemp in parent dir + os.fsync + os.replace"
    - "Boot-time .tmp sweep: DiagnosticsSink.__init__ walks rglob('*.tmp') and unlinks non-symlink entries whose resolved path is under the root"
    - "Path-traversal defence: open_validation sanitises mechanic_id via [^A-Za-z0-9_.-] -> '_' then re-verifies resolved path via relative_to(root)"
    - "Symlink-safe prune: candidates filtered by is_symlink() and re-verified against root before shutil.rmtree"
    - "Sink wiring via optional kwarg: scan() keeps the no-arg contract; callers that want diagnostics pass the sink explicitly"
    - "Sink-write failures degrade to warnings.warn (registry's primary contract is indexing, not diagnostics)"
key-files:
  created:
    - src/token_world/mechanic/diagnostics.py
    - tests/test_mechanic/test_diagnostics.py
    - tests/test_cli/test_prune_diagnostics.py
  modified:
    - src/token_world/mechanic/__init__.py (public exports)
    - src/token_world/mechanic/registry.py (scan kwarg + helpers)
    - src/token_world/cli.py (prune-diagnostics command)
    - tests/test_mechanic/test_registry.py (TestRegistrySinkWiring)
    - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md (T1-T5 rows)
    - .planning/phases/04-llm-mechanic-generation/deferred-items.md (04-03 discoveries section)
decisions:
  - Applied D-21..D-25 literally. summary.json schema stamped with SCHEMA_VERSION=1 at the top.
  - finalize() promotes status='pending' (initial placeholder) to 'ok' so readers never see a stuck tick when the caller omits set_summary.
  - Sink-wiring kwarg, not a constructor attr. scan(diagnostics_sink=...) keeps backward compat and doesn't pollute __init__.
  - Registry derives mechanic_id by falling back to module_path.stem when ValidationReport lacks an explicit id (current dataclass shape).
  - CLI exit codes: 0 success, 1 missing universe, 2 usage error — consistent with validate-mechanic.
metrics:
  duration: ~35 min
  completed: 2026-04-12
---

# Phase 4 Plan 03: Diagnostics substrate + prune-diagnostics CLI + D-15 closure — Summary

AUTO-02 delivered: a filesystem substrate for per-tick + per-validation
diagnostics, atomic JSON writes, schema versioning, symlink-safe manual
pruning, and — the bonus closure — ``MechanicRegistry.scan()`` now persists
every failing ``ValidationReport`` to
``universe/diagnostics/validation/<ts>_<id>/report.json``, closing the
D-15 wiring loop that 04-02 left open.

## Final API Surface

```python
SCHEMA_VERSION: int = 1

class DiagnosticsSink:
    def __init__(self, universe_dir: Path) -> None: ...
    @property
    def root(self) -> Path: ...
    @contextmanager
    def open_tick(self, tick_id: int) -> Iterator[TickDiagnostics]: ...
    def open_validation(self, mechanic_id: str) -> Path: ...
    def prune(self, *, before_tick: int | None = None,
              before_date: date | None = None,
              confirm: bool = False) -> list[Path]: ...

class TickDiagnostics:
    tick_id: int
    @property
    def dir(self) -> Path: ...
    def write_action(self, text: str) -> None: ...
    def write_classification(self, *, prompt: str, response: str, parsed: dict) -> None: ...
    def write_matching(self, matched: list[dict]) -> None: ...
    def append_mutation(self, mutation_dict: dict) -> None: ...
    def write_execution_trace(self, trace_dict: dict) -> None: ...
    def write_observation(self, *, prompt: str, response: str, parsed: dict) -> None: ...
    def set_summary(self, **fields: Any) -> None: ...
    def finalize(self) -> None: ...   # idempotent; called from __exit__


# Registry extension (Task 4)
def MechanicRegistry.scan(self, *,
                          diagnostics_sink: DiagnosticsSink | None = None
                          ) -> list[ValidationReport]: ...
```

## Directory Layout (D-21 / D-22)

```
universe/diagnostics/
├── tick_<id>/
│   ├── action.txt
│   ├── classification/{prompt.txt, response.txt, parsed.json}
│   ├── matching.json
│   ├── execution/{trace.json, mutations.jsonl}
│   ├── observation/{prompt.txt, response.txt, parsed.json}
│   └── summary.json                    # {"schema_version": 1, "tick_id": N, "status": "ok"|"error"|..., ...}
└── validation/<YYYYMMDDThhmmssZ>_<safe_id>/
    └── report.json                      # ValidationReport.to_dict()
```

``safe_id`` = mechanic id sanitised via ``[^A-Za-z0-9_.-] → '_'``;
resulting folder is re-verified under root via
``Path.resolve().relative_to(self._root)``.

### summary.json schema v1

```json
{
  "schema_version": 1,
  "tick_id": 123,
  "status": "ok",
  "... caller-supplied fields ...": "..."
}
```

Readers: check ``schema_version == 1``, treat unknown keys as forward-
compatible extensions. When the schema bumps, the constant in
``diagnostics.py`` flips and callers can branch.

## What Changed

### New module `src/token_world/mechanic/diagnostics.py` (Task 1)
- ``SCHEMA_VERSION = 1`` public constant, exported from the package.
- ``_atomic_write_json(path, obj)`` — tempfile in same dir + fsync +
  ``os.replace``. Leftovers on crash end in ``.tmp``; next ``DiagnosticsSink``
  boot sweeps them.
- ``DiagnosticsSink``:
  - ``__init__(universe_dir)`` creates ``diagnostics/`` and sweeps ``*.tmp``.
  - ``open_tick(n)`` context manager yields ``TickDiagnostics``; ``finalize``
    runs on exit.
  - ``open_validation(mechanic_id)`` returns a sanitised, root-verified
    folder path.
  - ``prune(...)`` iterates tick and validation candidates, filters
    symlinks, re-verifies paths, rmtree only on ``confirm=True``.
- ``TickDiagnostics``:
  - ``write_action / write_classification / write_matching /
    append_mutation / write_execution_trace / write_observation /
    set_summary / finalize``.
  - ``summary.json`` gets ``status='pending'`` at init, upgraded to
    ``'ok'`` at ``finalize`` if the caller never set it explicitly.

### Tests (Task 2)
- 26 tests in ``tests/test_mechanic/test_diagnostics.py`` covering:
  - Root creation, schema assertions, atomic write (no ``.tmp`` leftovers).
  - Writer coverage: action, classification, matching, mutations (jsonl),
    execution trace, observation.
  - ``open_validation`` timestamp format + sanitisation + empty-id fallback.
  - Boot-time cleanup of stale ``.tmp`` + symlink-escape defence.
  - ``prune`` by-tick / by-date / dry-run / confirm / symlink refusal /
    external-target protection / empty result.
  - ``finalize`` idempotency + implicit flush on exception.

### CLI + VALIDATION (Task 3)
- ``src/token_world/cli.py`` gains ``prune-diagnostics``:
  - ``token-world prune-diagnostics <slug> [--before-tick N | --before-date YYYY-MM-DD] [--confirm]``.
  - Exactly-one-cutoff enforcement; ``--confirm`` off by default.
  - Human-readable output with ``Would delete N ...`` or ``Deleted N ...``
    plus the candidate paths relative to the universe folder.
  - Exit codes: ``0`` success, ``1`` missing universe, ``2`` usage error.
- 6 CLI tests (``tests/test_cli/test_prune_diagnostics.py``) via Click's
  ``CliRunner``: usage-errors, date validation, dry-run listing,
  ``--confirm`` deletion, missing-universe exit 1, ``--help`` contains
  ``--confirm``.
- ``04-VALIDATION.md`` gains rows ``04-03-T1 .. 04-03-T4``.
- Pre-existing lint/format drift in ``validation.py`` (commit ``a6c1491``)
  logged to ``deferred-items.md`` — out of scope per CLAUDE.md §4.

### Registry → Sink wiring (Task 4)
- ``MechanicRegistry.scan()`` gains optional ``diagnostics_sink`` kwarg.
- When present, every failing ``ValidationReport`` is written to
  ``universe/diagnostics/validation/<ts>_<id>/report.json`` via
  ``DiagnosticsSink.open_validation`` + ``_atomic_write_json``.
- ``_write_validation_diagnostics`` helper catches ``OSError`` /
  ``ValueError`` and degrades them to ``warnings.warn``; the registry's
  indexing path is never broken by a sink failure.
- Mechanic id derivation: prefers ``report.mechanic_id`` (forward-compat
  if 04-02's dataclass gains one) and falls back to
  ``report.module_path.stem``.
- 3 new tests in ``TestRegistrySinkWiring``:
  1. ``test_registry_writes_validation_failure_via_sink`` — happy path.
  2. ``test_registry_scan_without_sink_is_unchanged`` — backward compat.
  3. ``test_registry_sink_write_failure_is_warned_not_raised`` —
     OSError fallback via monkeypatched ``open_validation``.
- ``04-VALIDATION.md`` row ``04-03-T5``.

## Test Counts

- **Before plan:** 364 passed.
- **After plan:** 399 passed (+35 = 26 diagnostics + 6 CLI + 3 registry-wiring).
- **Lint (src/ files touched by this plan):** ``ruff check`` clean on
  ``diagnostics.py`` + ``cli.py`` + ``registry.py``.
- **Format (src/ files touched by this plan):** ``ruff format --check`` clean.
- **mypy:** ``mypy src/token_world/mechanic/`` clean (15 source files).

Pre-existing regressions not owned by this plan (documented in
``deferred-items.md``):
- ``src/token_world/mechanic/validation.py`` has 2 × E501 and a format
  diff from commit ``a6c1491``.

## Deviations from Plan

### Auto-fixed / in-scope adjustments

**1. [Rule 1 - Bug] ``status`` stayed at the ``"pending"`` placeholder.**
- **Found during:** Task 2 running ``test_status_defaults_to_ok_when_unset``.
- **Issue:** ``TickDiagnostics.__init__`` seeds ``_summary["status"] = "pending"``.
  The original ``finalize()`` used ``setdefault("status", "ok")``, which is
  a no-op when the key already exists. Readers would see ``"pending"``
  forever when the caller skipped ``set_summary``.
- **Fix:** ``finalize`` now replaces ``"pending"`` with ``"ok"`` before the
  atomic write. Any explicit status (``"error"``, ``"timeout"``, ...) is
  preserved.
- **Files modified:** ``src/token_world/mechanic/diagnostics.py``.
- **Commit:** ``d1d6819``.

**2. [Rule 1 - Test] ``..`` substring in sanitised folder name.**
- **Found during:** Task 2 running
  ``test_open_validation_sanitizes_dangerous_mechanic_id``.
- **Issue:** Plan suggested asserting ``".." not in folder.name``. But the
  allow-list ``[A-Za-z0-9_.-]`` intentionally keeps ``.`` and ``-``, so
  ``"../../../etc/passwd"`` becomes ``"_.._.._.._etc_passwd"`` — which
  contains ``..`` as a substring even though the path can no longer be used
  to escape.
- **Fix:** Adjusted the assertion to the actual security contract: the
  resolved path is under the diagnostics root and contains no path
  separators (``/``, ``\``). The ``".." not in`` check was a proxy for
  the real property, not the property itself.
- **Files modified:** ``tests/test_mechanic/test_diagnostics.py``.
- **Commit:** ``d1d6819``.

## Threat Flags

None. All surface introduced by this plan is covered by the plan's
``<threat_model>`` register (T-04-DIAG-PATH-TRAVERSAL,
T-04-DIAG-JSON-INJECTION, T-04-PRUNE-DESTRUCTION, T-04-TMP-LEAK). No new
endpoints, auth paths, or schema changes at a trust boundary beyond what
the plan anticipated.

## Notes for Downstream Plans

- **Phase 5 / resume_tick orchestrator** wires the per-tick sink as:
  ```python
  sink = DiagnosticsSink(universe_dir)
  with sink.open_tick(tick_id) as ctx:
      ctx.write_action(raw)
      ctx.write_classification(prompt=..., response=..., parsed=...)
      ctx.write_matching(...)
      # ... mechanic chain execution ...
      ctx.write_execution_trace(trace.to_dict())
      for mut in mutations:
          ctx.append_mutation(mut.to_dict())
      ctx.write_observation(prompt=..., response=..., parsed=...)
      ctx.set_summary(mechanics_fired=[...], tokens=..., duration_ms=...)
  # finalize runs on __exit__
  ```
  The sink should be constructed once per resume_tick call (cheap —
  `.resolve()` twice plus a tmp-sweep).
- **Phase 5 registry wiring:** where resume_tick re-scans mechanics,
  pass the sink:
  ```python
  registry.scan(diagnostics_sink=sink)
  ```
  The ``__init__``-time scan inside ``MechanicRegistry(mechanics_dir, ...)``
  does NOT take the sink — callers who want diagnostics must call
  ``scan`` explicitly once the universe + sink are constructed.
- **04-04 integration harness:** use ``sink.open_tick(tick_id)`` for each
  parametrized use case. The harness should set
  ``summary["status"] = "yield"`` for use cases where no mechanic matches
  (D-29b yield outcome) and ``summary["status"] = "blocked_by_framework_gap"``
  for stubs waiting on Phase 5 framework extensions (D-38). Both are just
  string values in the JSON; readers distinguish them by the ``status``
  field alone. ``summary["status"] = "ok"`` is the pass case.
- **Retention / prune:** there's no auto-rotation. Universes that accumulate
  many ticks need an explicit
  ``token-world prune-diagnostics <slug> --before-tick N --confirm``.
  Document this in the universe CLAUDE.md template (04-05 authoring guide)
  so operators know the knob exists.
- **Schema version bumps:** when the per-tick schema changes, bump
  ``SCHEMA_VERSION`` in ``diagnostics.py`` and update readers to branch
  on it. Validation schema (``validation/*/report.json``) mirrors
  ``ValidationReport.to_dict()``; if that shape changes, the version
  constant should also change.

## Commits

| Task | Commit  | Type | Summary |
|------|---------|------|---------|
| T1   | a7d791c | feat | add DiagnosticsSink + TickDiagnostics (AUTO-02) |
| T2   | d1d6819 | test | DiagnosticsSink lifecycle + security coverage |
| T3   | ebae342 | feat | prune-diagnostics CLI + VALIDATION map rows T1-T4 |
| T4   | 779d6a9 | feat | wire MechanicRegistry.scan -> DiagnosticsSink (D-15 closure) |

## Self-Check: PASSED

- All 4 per-task commits present on branch:
  ``git log --oneline -4`` → a7d791c, d1d6819, ebae342, 779d6a9.
- Files created:
  - ``src/token_world/mechanic/diagnostics.py`` ✓
  - ``tests/test_mechanic/test_diagnostics.py`` ✓
  - ``tests/test_cli/test_prune_diagnostics.py`` ✓
- Files modified:
  - ``src/token_world/mechanic/__init__.py`` (exports) ✓
  - ``src/token_world/mechanic/registry.py`` (scan kwarg + helpers) ✓
  - ``src/token_world/cli.py`` (prune-diagnostics command) ✓
  - ``tests/test_mechanic/test_registry.py`` (TestRegistrySinkWiring) ✓
  - ``.planning/phases/04-llm-mechanic-generation/04-VALIDATION.md``
    (rows T1-T5) ✓
  - ``.planning/phases/04-llm-mechanic-generation/deferred-items.md``
    (04-03 section) ✓
- Phase gate:
  - ``uv run pytest -x -q`` → 399 passed ✓
  - ``uv run ruff check src/token_world/mechanic/diagnostics.py
    src/token_world/mechanic/registry.py src/token_world/cli.py`` → clean ✓
  - ``uv run ruff format --check`` on our files → clean ✓
  - ``uv run mypy src/token_world/mechanic/`` → clean ✓
- Acceptance greps:
  - ``SCHEMA_VERSION = 1`` in diagnostics.py: 1 match ✓
  - ``class DiagnosticsSink`` + ``class TickDiagnostics``: 2 matches ✓
  - ``os.replace`` / ``tempfile.mkstemp``: 5 matches ✓
  - ``resolve().relative_to`` / ``resolved.relative_to``: 4 matches ✓
  - ``open_validation`` / ``diagnostics_sink`` /
    ``_write_validation_diagnostics`` in registry.py: 9 matches ✓
- CLI smoke:
  ``uv run token-world prune-diagnostics --help`` → documents ``--confirm`` ✓
