# Phase 4: Mechanic Authoring & Validation Infrastructure — Research

**Researched:** 2026-04-12
**Domain:** Python module loading + AST static analysis + pytest parametrization + filesystem-backed diagnostics
**Confidence:** HIGH (core patterns are Python stdlib; existing codebase verified directly)

## Summary

Phase 4 is unusual: no new library needs to be chosen. Every decision from CONTEXT.md maps to a narrow pattern already present in the Python stdlib (`ast`, `importlib.util`, `pathlib`, `tempfile`) or existing project infrastructure (Click CLI, pytest, `KnowledgeGraph`, `GraphBuilder`). The planner's job is therefore **mechanical decomposition** — not tool selection — across five infrastructure deliverables and one large authoring campaign (27 seed mechanics).

The highest-leverage research findings are:

1. The existing loader/registry is a 20-minute rewrite, **not** a refactor. `loader.load_mechanic_class` is a single function that imports `<dir>/mechanic.py` and returns the first `Mechanic` subclass. Switching to module-based discovery is a straight swap: iterate `*.py` files, skip `_*.py` and `__init__.py`, for each collect all `Mechanic` subclasses and index by `cls.id`. The registry's current fallback-to-class-attributes path already handles the "no meta.yaml" case, so dropping `meta.yaml` entirely simplifies rather than complicates.
2. **No sandboxing research is needed.** v1 runs `exec_module` by design (confirmed in CLAUDE.md, Phase 0 I-01 review finding). AST rules are a static gate, not a runtime sandbox. RestrictedPython/CVE-2025-22153 concerns in STATE.md can be resolved by stating explicitly: "AST rules enforce authoring discipline; they are not a security boundary. Runtime sandboxing deferred to v2." This is consistent with D-14.
3. Validation pipeline composition — syntax → AST → import → contract → tests → dry-execute — maps one-to-one onto stdlib primitives: `ast.parse`, a custom `ast.NodeVisitor`, `importlib.util.spec_from_file_location`, `inspect.isclass` + `issubclass`, `subprocess.run(["pytest", ...])`, instantiate-and-call. No framework choice needed.
4. Integration test harness is a pytest-parametrize-from-YAML pattern. The Phase-3 `load_use_case` loader already returns `(frontmatter_dict, markdown_body)` with shape-validated gaps list — exactly what the harness needs. The D-29b tri-state outcome (pass / yield / blocked-by-framework-gap / fail) maps to pytest markers (`@pytest.mark.parametrize` with `pytest.param(..., marks=pytest.mark.xfail(reason=...))` or `pytest.mark.skip(reason=...)`).
5. **Diagnostics schema is operationally thin.** `DiagnosticsSink` is a context-manager class writing JSON/JSONL/text files under `universe/diagnostics/tick_<id>/`. Atomic writes via `NamedTemporaryFile(dir=..., delete=False) + os.replace(...)` are stdlib-standard (POSIX atomic rename; Windows `os.replace` semantics are equivalent in Python 3.3+).
6. Seed-mechanic authoring (27 files) is the **risk-concentrated** work. Clustering by shared helpers and shared framework-gap dependencies is the key planning lever. Dependency graph (below) is sparse — only a few mechanics share `_helpers.py`, and framework-gap-blocked stubs are clearly identifiable.

**Primary recommendation:** Treat Phase 4 as five small infrastructure plans (04-01 through 04-05) followed by 4-7 parallel seed-authoring waves. Infrastructure plans have no external dependencies and can be sequenced quickly; seed waves gate on 04-02 (validation) and 04-04 (integration harness) being green. Target ~20-30 plan files total.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

The following decisions from `04-CONTEXT.md` are authoritative. Plans MUST implement them exactly; research below assumes these are fixed.

- **D-01/D-02 — Inversion of control.** Top-level coding agent (Opus via Claude Code + Agent SDK) authors mechanics with normal file-writing tools. No bespoke LLM generation pipeline. "MECH-03 LLM generates valid Python mechanics" is satisfied by operator-authored code passing Phase 4's validation pipeline.
- **D-03 — Flat layout.** Mechanics are flat Python modules at `mechanics/<id>.py`. One `Mechanic` subclass per file by default. Multi-mechanic files allowed but not enforced.
- **D-04 — Class attributes replace meta.yaml.** `Mechanic` base declares defaults: `id: str` (required), `description: str` (required), `voluntary: bool = True`, `tags: list[str] = []`. `meta.yaml` files are deleted from seeds; the scaffold never creates them.
- **D-05 — Underscore helpers.** Shared helpers live as `mechanics/_helpers.py`, `mechanics/_spatial.py`, etc. Registry skips files starting with `_` during discovery.
- **D-06 — Tests NOT colocated.** Tests live in the project's test tree, mirroring module layout. Built-in seeds: `tests/test_mechanic/test_seeds/test_<id>.py`. Universe-local: `universe/tests/test_mechanics/test_<id>.py`.
- **D-07 — Module-based discovery.** Loader imports every `<name>.py` in the mechanics directory where `<name>` does not start with `_` and is not `__init__.py`; collects all classes that subclass `Mechanic` (excluding `Mechanic` itself); indexes by `cls.id`.
- **D-09/D-10 — Seed flattening + scaffolding.** Flatten seeds: `seeds/movement.py`, `seeds/observation.py`, `seeds/environmental_reaction.py`, `seeds/_helpers.py` (empty at first). Scaffold copies flat `.py` files into `universe/mechanics/` and creates `universe/tests/test_mechanics/` with mirrored starter tests. Scaffolding never creates subfolders inside `mechanics/`.
- **D-12 — Single validation implementation.** `token_world.mechanic.validation.validate(module_path: Path) -> ValidationReport`. All entry points (CLI, registry auto-scan) call it.
- **D-13 — Validation stages (atomic; stop at first hard failure; accumulate non-blocking warnings):** syntax (ast.parse) → static AST rules → import → class contract → own tests pass → dry-execute smoke.
- **D-14 — AST rules.** Forbidden imports: `networkx`, `networkx.*`, `token_world.graph.knowledge_graph`. Forbidden calls: `eval`, `exec`, `__import__`, `compile`, `globals`, bare `open` (pathlib wrapping allowed for pytest fixtures). Required: ≥1 class subclassing `Mechanic` with class-level `id: str` and `description: str`. Allowed: `token_world.mechanic.*` public API, sibling `_*.py` helpers, Python stdlib.
- **D-15 — Entry points.** CLI `validate-mechanic <universe> <id-or-path>` — structured report, exit code 0/nonzero. Registry auto-scan on every `resume_tick` validates; invalid mechanics are excluded from the live index and failures logged to `diagnostics/validation/<timestamp>_<mechanic-id>/report.json`.
- **D-16 — ValidationReport shape.** Includes: failing stage, triggered rule, file:line:column (for AST stages), message, accumulated non-blocking warnings.
- **D-17 — No retry/repair pipeline.** Operator iterates naturally (edit → re-run validation). No prompt-repair plumbing.
- **D-18 — No prompt-assembly pipeline.** Operator reads the codebase + guides to orient. Phase 4 ships high-quality guides.
- **D-19/D-20 — 3-tool MCP surface.** Drop `register_mechanic`. Minimal tools: `resume_tick`, `rollback`, `list_mechanics`. Update MCP stub server, universe CLAUDE.md template, and all tests that reference `register_mechanic` in plan 04-01.
- **D-21 — Per-tick diagnostics layout.** `universe/diagnostics/tick_<tick_id>/` with subfolders `classification/`, `execution/`, `observation/`, plus top-level `action.txt`, `matching.json`, `summary.json`. Exact schema per CONTEXT.md D-21 is fixed.
- **D-22 — Validation diagnostics layout.** `universe/diagnostics/validation/<iso_timestamp>_<mechanic-id>/` with `report.json`, optional `ast_errors.json`, optional `test_output.txt`.
- **D-23 — DiagnosticsSink API.** Methods `sink.open_tick(tick_id)`, `ctx.write_prompt(...)`, `ctx.write_response(...)`, `sink.close_tick(summary)`. Phase 5 wires classifier/observer calls; Phase 4 exercises via validation + integration tests.
- **D-24 — Schema versioning.** `summary.json` carries `"schema_version": 1`.
- **D-25 — Retention.** No automatic rotation in v1. CLI `prune-diagnostics <universe> [--before-tick N | --before-date YYYY-MM-DD]`.
- **D-26/D-27 — Integration harness.** Pytest-based at `tests/test_integration/test_use_cases.py`. Constructs `KnowledgeGraph` from use-case precondition state; invokes Phase 2 chain execution; asserts mutations + observation-relevant state + expected involuntary chain.
- **D-28 — Consume existing loader.** `src/token_world/use_cases/loader.py` already exists and MUST NOT be reimplemented. Phase 4 fixes CRLF bug (M-04) and consumes directly.
- **D-29/D-29b — Coverage model.** pass / yield ("no matching mechanic" = valid per declared expected result) / blocked-by-framework-gap / fail.
- **D-30/D-31 — Authoring guides.** `docs/guides/authoring-mechanics.md` (framework-level) + copy into scaffolded universe; universe CLAUDE.md gets a "Mechanic Authoring" section linking to it.
- **D-32 — scaffold-mechanic CLI.** `scaffold-mechanic <universe> --id <id> [--voluntary|--involuntary]` — emits skeleton module + test stub.
- **D-33 — Phase 3 fixes in 04-01.** H-01 (`TemporalIndex.find_state_at_tick` ignores `add_node`) + M-04 (CRLF frontmatter).
- **D-34 — GAP-ENG16 split.** Phase 5 classifier returns `no_viable_action` for nonsense; Phase 4 validation gate rejects bad mechanics. No "manual-review queue."
- **D-35 — GAP-MECH19 obsolete.** No trust boundary; all mechanics are operator-authored and validated.
- **D-36/D-37/D-38 — Seed mechanic authoring is in-phase.** Author MECH01–MECH27 in thematic clusters. Some (e.g., MECH09/MECH12) ship as framework-gap stubs that declare their dependency and integration tests mark as "blocked".

### Claude's Discretion

- D-11 — Code-reuse style (free functions in `_*.py` vs base-class inheritance). Default: free functions; base classes only when ≥3 mechanics share a pattern.
- D-32 — `scaffold-mechanic` emits full test stub vs class skeleton only.
- D-37 — Exact seed-mechanic clustering per plan. CONTEXT.md suggests groupings; planner picks cluster boundaries.
- `validate-mechanic` CLI output format (human-readable vs JSON vs both via `--format`).
- Whether test-execution stage RUNS the mechanic's tests vs just verifies they exist. Default per CONTEXT.md: runs them.
- Whether `_helpers.py` is scaffolded empty vs omitted until needed.

### Deferred Ideas (OUT OF SCOPE)

- Runtime sandboxing (RestrictedPython) — v2 hardening.
- Automatic diagnostics rotation — `prune-diagnostics` is manual.
- Lazy mechanic loading — eager import is acceptable until counts grow.
- Dedicated `.claude/skills/author-mechanic/` skill inside scaffolded universes.
- Coherence checking (HARD-02).
- Cost monitoring / circuit breakers (HARD-03).
- Multi-mechanic-per-file conventions — default one-per-file; no guidance until a real case appears.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **MECH-03** | LLM generates valid Python mechanics using the framework from agent action context | Reframed per D-01/D-02: operator (Opus) authors mechanics; "generates" = SDLC. The validation pipeline (D-12..D-16, §Validation Pipeline Architecture below) is the acceptance criterion. Authoring guides (D-30, §Authoring Guide Content) + scaffold-mechanic CLI (D-32) support the workflow. Satisfied by plans 04-02, 04-05, and the seed waves (each seed is a successful "generation" via the operator). |
| **MECH-04** | Generated mechanics are validated (syntax, AST checks) before execution | Validation pipeline directly addresses this: 6-stage pipeline with hard-fail + accumulated warnings (§Validation Pipeline Architecture). AST rules enforced via `ast.NodeVisitor` subclass (§AST Walker Design). Entry points: CLI + registry auto-scan (§Registry Auto-Scan Caching). Plan 04-02. |
| **MECH-05** (revised) | Each mechanic is a Python module `mechanics/<id>.py` with class-level attributes; versioned by universe git; shared helpers via `_*.py` | Plan 04-01 rewrites loader + registry. Git versioning is unchanged (still `git log -- mechanics/<id>.py` per D-08). §Module-Based Discovery Pattern. |
| **MECH-06** (revised) | Registry indexes by importing modules and collecting `Mechanic` subclasses | Rewritten `MechanicRegistry.scan()`: iterate `*.py`, skip `_*.py` + `__init__.py`, import each, collect all subclasses, index by `cls.id`. §Module-Based Discovery Pattern. Plan 04-01. |
| **TEST-02** | Integration tests for multi-mechanic chains with realistic graph state | Pytest harness at `tests/test_integration/test_use_cases.py` parametrized from `load_use_case(...)` output; chain execution via existing `ChainExecutionEngine`; outcome marking via `pytest.param(..., marks=...)` (§Integration Test Harness Pattern). Plan 04-04. |
| **AUTO-02** | Diagnostics filesystem — each simulation turn can dump prompts, responses, parsed output | `DiagnosticsSink` class with context-manager pattern + atomic writes (§Diagnostics Filesystem Schema & Sink). Schema versioning via `summary.json`. Plan 04-03 implements; Phase 5 wires in. |
| **UNIV-03** (revised) | Generated `.mcp.json` exposes minimal simulation tools `resume_tick`, `rollback`, `list_mechanics` (dropping `register_mechanic`) | String/assertion updates across `mcp_server.py`, `templates/claude_md.py`, and tests (§MCP Tool Surface Reduction). Plan 04-01. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

Plans MUST honor the following project directives:

- **Python 3.12+** — type hints required; use modern `|` syntax; `from __future__ import annotations` in every module.
- **Graph mutations only through `KnowledgeGraph` API.** Enforced by AST rules (D-14 forbids `token_world.graph.knowledge_graph` direct import in mechanic modules).
- **JSON-serializable properties only** — `ALLOWED_PROPERTY_TYPES = (str, int, float, bool, None, list, dict)`. Diagnostics `summary.json` / `mutations.jsonl` must also be JSON-serializable (they already are — `Mutation` is a dataclass of simple fields).
- **Two node types: `agent` and `entity`** — every seed mechanic that adds nodes must use these.
- **Raw `sqlite3` only — no ORM.** Not directly relevant to Phase 4 deliverables (diagnostics are filesystem-based, not DB), but applies to any incidental SQLite work (none expected).
- **No pickle.** Diagnostics use JSON/JSON-lines/plain text only.
- **`uv` for package management.** New dependencies (none expected — stdlib only) go through `uv add`.
- **`ruff` for lint/format, `mypy` for types, `prek` for hooks, `pytest` for tests.** New test files follow `tests/test_*/` convention with mirrored layout.
- **Node IDs via `kg.claim_id(...)`** — seed mechanics that create new nodes (e.g., MECH14 craft output) must use this.
- **Use `GraphBuilder` from `tests/test_graph/conftest.py`** for test setup. Integration harness reuses this (D-27).

**No CLAUDE.md directive conflicts with any locked decision.**

## Standard Stack

### Core — already in project

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ast` (stdlib) | 3.12 | Static AST analysis for D-14 rules | Python's canonical AST API. `ast.parse` + `ast.NodeVisitor` is the textbook pattern for source-level linting (bandit, pylint, flake8 plugins all use it). [VERIFIED: stdlib imported successfully] |
| `importlib.util` (stdlib) | 3.12 | Dynamic module import | Already in use in `mechanic/loader.py:34-39` — `spec_from_file_location` + `module_from_spec` + `loader.exec_module`. [VERIFIED: grep of `src/token_world/mechanic/loader.py`] |
| `inspect` (stdlib) | 3.12 | Class introspection (`isclass`, signature comparison) | Already in use in `mechanic/loader.py:41-43`. [VERIFIED: grep of existing code] |
| `subprocess` (stdlib) | 3.12 | Invoke `pytest` for D-13 stage 5; invoke `git log` for mechanic versioning | Already used in `registry.py:186-199` (git log) and `tests/test_mechanic/test_registry.py:49-57` (git init). [VERIFIED] |
| `click` | 8.0+ | CLI entry points (`validate-mechanic`, `scaffold-mechanic`, `prune-diagnostics`) | Already the project CLI framework — `cli.py` defines `cli = click.group()`. Adding new commands is an `@cli.command("name")` decorator. [VERIFIED: `pyproject.toml` line 12] |
| `pytest` | 8.x/9.x | Integration harness + validation stage 5 | Already configured; `pyproject.toml` `[tool.pytest.ini_options]` sets `testpaths = ["tests"]`, `pythonpath = ["src"]`. [VERIFIED: `pyproject.toml`] |
| `pyyaml` | 6.0.3+ | Use-case manifest frontmatter parsing | Already consumed via `use_cases/loader.py`. Do NOT add new YAML surface in Phase 4 — Phase 3 already defined the format. [VERIFIED] |
| `NetworkX` | 3.6+ | Graph — indirect only (mechanics go through `MechanicContext`) | v1 stack constraint. Listed for completeness — Phase 4 does not touch NetworkX directly. |

### Supporting — stdlib patterns, no new deps needed

| Pattern | Module | Purpose | When to Use |
|---------|--------|---------|-------------|
| Atomic file write | `tempfile.NamedTemporaryFile` + `os.replace` | Diagnostics write-then-rename so partial writes never leave corrupt files | Every `sink.close_tick(...)` call writing `summary.json`; every mutation line append [CITED: docs.python.org/3/library/os.html#os.replace] |
| ISO timestamp | `datetime.datetime.now(UTC).isoformat()` | `diagnostics/validation/<iso_timestamp>_<mechanic-id>/` directory names | Replace `:` with `-` for filesystem safety on Windows; plan uses `strftime("%Y%m%dT%H%M%SZ")` |
| Context manager | `contextlib.contextmanager` or `__enter__`/`__exit__` | `DiagnosticsSink.open_tick()` returning a context object | Ensures `close_tick()` fires even on exception |
| JSON-lines append | `path.open("a", encoding="utf-8") as f: f.write(json.dumps(obj) + "\n")` | `mutations.jsonl` one-per-line | Avoid JSON-array-per-file — incremental append + easy `grep`/line-count |
| Pytest parametrize with marks | `pytest.param(value, marks=pytest.mark.xfail(reason="..."))` | Use-case-driven harness outcome coding | D-29b distinguishes pass/yield/blocked/fail [CITED: docs.pytest.org/en/stable/reference/reference.html#pytest-param] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `ast.NodeVisitor` | `bandit` plugin API, `pylint` checker API, `flake8` plugin | Heavier — we want 5-10 rules, not a plugin ecosystem. Custom visitor is ~100 LOC and testable in isolation. [ASSUMED: bandit/pylint overhead; verify if scope grows past 15 rules] |
| Custom `ast.NodeVisitor` | `ruff` with custom rules | Ruff plugin support is still limited as of early 2026; forking ruff is overkill. Stick to stdlib `ast`. [ASSUMED: verify ruff plugin status before committing — if ruff plugins mature, plan 04-02 could revisit] |
| Write-then-rename atomic | `fsync` + `rename` | Python `os.replace` is atomic on POSIX and Windows (since 3.3); `fsync` adds crash-durability guarantees. For diagnostics (not critical state), `os.replace` is sufficient. Crash during tick = diagnostics for that tick may be incomplete; acceptable. [VERIFIED: Python docs] |
| `json.dumps(obj, default=str)` | `json.dumps(obj)` | Mutations include `None`, `list`, `dict`; no custom serializers needed since `Mutation` is a dataclass of primitives. Use `dataclasses.asdict(m)` then `json.dumps` to keep schema transparent. |
| Yaml parametrization in pytest | `pytest-yaml` plugin | Adds dependency for one use case. `load_use_case(path)` + explicit `@pytest.mark.parametrize` covers it cleanly. |
| `tempfile.NamedTemporaryFile(dir=...)` for atomic writes | `Path.write_text` + hope | `write_text` is NOT atomic — a crash mid-write truncates. Atomic pattern matters for `summary.json` because it's written once per tick and should be all-or-nothing. |

**Installation:** No new dependencies. All pieces are stdlib or already in `pyproject.toml`. [VERIFIED: `pyproject.toml` inspection]

**Version verification:**
- `uv 0.9.24`, `pytest 7.0.0` (pyproject says `pytest>=9.0` — local env may lag; plans should rely on pyproject declaration), Python 3.12. [VERIFIED: `uv --version`, `pytest --version`]

## Architecture Patterns

### Recommended File Layout (Phase 4 additions)

```
src/token_world/
├── mechanic/
│   ├── loader.py              # REWRITTEN — module-based discovery (D-07)
│   ├── registry.py            # REWRITTEN — drops meta.yaml; reads class attrs (D-04)
│   ├── protocol.py            # MODIFIED — Mechanic gains `tags: list[str] = []` class default
│   ├── validation.py          # NEW — validate() entry + ValidationReport dataclass + AST visitor
│   ├── diagnostics.py         # NEW — DiagnosticsSink + per-tick context
│   └── seeds/
│       ├── __init__.py
│       ├── _helpers.py        # NEW (empty stub; grows as seed clusters share code)
│       ├── movement.py        # MOVED from seeds/movement/mechanic.py
│       ├── observation.py     # MOVED from seeds/observation/mechanic.py
│       ├── environmental_reaction.py   # MOVED
│       ├── look.py            # NEW (MECH02)
│       ├── find_nearest.py    # NEW (MECH03)
│       ├── aoe.py             # NEW (MECH04)
│       ├── trade.py           # NEW (MECH07)
│       ├── give.py            # NEW (MECH08)
│       ├── persuade.py        # NEW (MECH09 — framework-gap stub)
│       ├── tell.py            # NEW (MECH10)
│       ├── teach.py           # NEW (MECH11)
│       ├── cooperate.py       # NEW (MECH12 — framework-gap stub)
│       ├── speak.py           # NEW (MECH13)
│       ├── craft.py           # NEW (MECH14)
│       ├── consume.py         # NEW (MECH15)
│       ├── pickup.py          # NEW (MECH16 — revised; honors inventory_cap)
│       ├── degrade.py         # NEW (MECH17)
│       ├── fungible_pay.py    # NEW (MECH18)
│       ├── fire_spread.py     # NEW (MECH20 — may extend existing environmental_reaction)
│       ├── weather_reaction.py # NEW (MECH21)
│       ├── decay_tick.py      # NEW (MECH22)
│       ├── illumination.py    # NEW (MECH23)
│       ├── contagion.py       # NEW (MECH24)
│       ├── belief_update.py   # NEW (MECH25)
│       ├── try_door.py        # NEW (MECH27)
│       ├── terrain_move.py    # NEW (MECH05 — extends movement)
│       ├── position_sync.py   # NEW (MECH06 — extends movement)
│       └── passage_move.py    # NEW (MECH01 — doorway traversal for UC-S01)
├── universe/
│   ├── scaffold.py            # MODIFIED — copies flat seed modules (no subdirs)
│   └── templates/
│       └── claude_md.py       # MODIFIED — 3-tool MCP surface + Mechanic Authoring section
├── mcp_server.py              # MODIFIED — TOOLS list drops register_mechanic
├── use_cases/loader.py        # MODIFIED — CRLF fix (M-04)
├── graph/temporal.py          # MODIFIED — H-01 add_node branch
└── cli.py                     # MODIFIED — adds validate-mechanic, scaffold-mechanic, prune-diagnostics

tests/
├── test_mechanic/
│   ├── test_loader.py         # REWRITTEN — module-based discovery
│   ├── test_registry.py       # REWRITTEN — no meta.yaml fixture
│   ├── test_validation.py     # NEW — per-stage + per-AST-rule coverage
│   ├── test_diagnostics.py    # NEW — sink lifecycle + atomic writes
│   └── test_seeds/            # NEW — D-06 mirrored layout
│       ├── test_movement.py   # MOVED from tests/test_mechanic/test_seed_movement.py
│       ├── test_observation.py
│       ├── test_environmental_reaction.py
│       ├── test_passage_move.py
│       └── ... (one per seed)
├── test_integration/
│   └── test_use_cases.py      # NEW — parametrized from load_use_case(...)
├── test_cli/
│   ├── test_validate_mechanic.py  # NEW
│   ├── test_scaffold_mechanic.py  # NEW
│   └── test_prune_diagnostics.py  # NEW
└── test_graph/
    └── test_temporal_index.py  # MODIFIED — H-01 regression test

docs/
└── guides/
    └── authoring-mechanics.md  # NEW (D-30)
```

### Pattern 1: Module-Based Discovery (D-07)

**What:** Replace folder-walking `load_mechanic_class(dir)` with module-iterating `load_mechanic_classes(module_path) -> list[type[Mechanic]]`.

**When to use:** Plan 04-01, rewriting `mechanic/loader.py`.

**Example:**
```python
# src/token_world/mechanic/loader.py (rewritten)
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from token_world.mechanic.protocol import Mechanic


def load_mechanic_classes(module_path: Path) -> list[type[Mechanic]]:
    """Import a mechanic module and return every Mechanic subclass it defines.

    Args:
        module_path: Path to the .py file (e.g., mechanics/movement.py).

    Returns:
        List of concrete Mechanic subclasses. Empty if the module defines none
        (that's a validation-pipeline concern, not an import-time error).

    Raises:
        FileNotFoundError: If module_path does not exist.
        ImportError: If the module fails to import.
    """
    if not module_path.is_file():
        raise FileNotFoundError(f"Mechanic module not found: {module_path}")

    module_name = f"mechanic_{module_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return [
        attr
        for _, attr in inspect.getmembers(module, inspect.isclass)
        if issubclass(attr, Mechanic) and attr is not Mechanic and attr.__module__ == module_name
    ]


def discover_mechanic_modules(mechanics_dir: Path) -> list[Path]:
    """Return the ordered list of mechanic module files in a directory.

    Skips __init__.py and any filename starting with '_' (helpers per D-05).
    """
    if not mechanics_dir.is_dir():
        return []
    return sorted(
        p
        for p in mechanics_dir.iterdir()
        if p.is_file()
        and p.suffix == ".py"
        and not p.name.startswith("_")
        and p.name != "__init__.py"
    )
```

The `attr.__module__ == module_name` filter prevents picking up `Mechanic` subclasses that were merely *imported* into the module (e.g., a helper module that imports the base class for typing).

### Pattern 2: AST Walker for D-14 Rules

**What:** Subclass `ast.NodeVisitor` to enforce forbidden imports / calls / required class contract. Single traversal, accumulates findings.

**When to use:** Plan 04-02, building `mechanic/validation.py`.

**Example sketch (full implementation ~150 LOC):**
```python
# src/token_world/mechanic/validation.py
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

FORBIDDEN_CALL_NAMES = frozenset({"eval", "exec", "__import__", "compile", "globals", "open"})
FORBIDDEN_IMPORT_PREFIXES = (
    "networkx",
    "token_world.graph.knowledge_graph",
)


@dataclass
class ValidationFinding:
    stage: str           # "syntax" | "ast" | "import" | "contract" | "tests" | "smoke"
    rule: str            # e.g., "forbidden_import", "missing_id_attr"
    severity: str        # "error" | "warning"
    message: str
    path: str
    line: int | None = None
    col: int | None = None


@dataclass
class ValidationReport:
    module_path: Path
    findings: list[ValidationFinding] = field(default_factory=list)
    passed: bool = True

    def fail(self, finding: ValidationFinding) -> None:
        self.findings.append(finding)
        if finding.severity == "error":
            self.passed = False


class _MechanicAstVisitor(ast.NodeVisitor):
    def __init__(self, module_path: Path) -> None:
        self.module_path = module_path
        self.errors: list[ValidationFinding] = []
        self.mechanic_classes: list[ast.ClassDef] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if any(alias.name == p or alias.name.startswith(p + ".") for p in FORBIDDEN_IMPORT_PREFIXES):
                self.errors.append(ValidationFinding(
                    stage="ast",
                    rule="forbidden_import",
                    severity="error",
                    message=f"Import of {alias.name!r} is forbidden in mechanics",
                    path=str(self.module_path),
                    line=node.lineno,
                    col=node.col_offset,
                ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_IMPORT_PREFIXES):
            self.errors.append(ValidationFinding(
                stage="ast",
                rule="forbidden_import",
                severity="error",
                message=f"Import from {mod!r} is forbidden in mechanics",
                path=str(self.module_path),
                line=node.lineno,
                col=node.col_offset,
            ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        name: str | None = None
        if isinstance(func, ast.Name):
            name = func.id
        if name in FORBIDDEN_CALL_NAMES:
            self.errors.append(ValidationFinding(
                stage="ast",
                rule="forbidden_call",
                severity="error",
                message=f"Call to {name!r} is forbidden in mechanics",
                path=str(self.module_path),
                line=node.lineno,
                col=node.col_offset,
            ))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Detect Mechanic subclasses by name. AST cannot resolve imports, so
        # we match any base named "Mechanic" (transitive subclasses are caught
        # later at the import stage).
        if any(isinstance(b, ast.Name) and b.id == "Mechanic" for b in node.bases):
            self.mechanic_classes.append(node)
        self.generic_visit(node)


def validate(module_path: Path) -> ValidationReport:
    """Run the 6-stage validation pipeline. Stop at first hard-failing stage."""
    report = ValidationReport(module_path=module_path)
    source = module_path.read_text(encoding="utf-8")

    # Stage 1: syntax
    try:
        tree = ast.parse(source, filename=str(module_path))
    except SyntaxError as e:
        report.fail(ValidationFinding(
            stage="syntax", rule="parse_error", severity="error",
            message=str(e), path=str(module_path), line=e.lineno, col=e.offset,
        ))
        return report

    # Stage 2: AST rules
    visitor = _MechanicAstVisitor(module_path)
    visitor.visit(tree)
    for err in visitor.errors:
        report.fail(err)
    if not visitor.mechanic_classes:
        report.fail(ValidationFinding(
            stage="ast", rule="no_mechanic_subclass", severity="error",
            message="Module defines no Mechanic subclass",
            path=str(module_path),
        ))
    if not report.passed:
        return report

    # Stage 3: import — see validation.py full implementation
    # Stage 4: class contract — verify id, description, check, apply
    # Stage 5: own tests pass — subprocess.run(["pytest", test_path, "-q"])
    # Stage 6: dry-execute smoke — instantiate + check(ctx) against minimal graph

    return report
```

**Confidence notes:**
- `ast.NodeVisitor` + `visit_Import` / `visit_ImportFrom` / `visit_Call` / `visit_ClassDef` is the canonical pattern for source-level linting. [VERIFIED: Python stdlib docs, used by bandit + flake8 widely]
- Lineno/col_offset are available on every AST node. [VERIFIED: ast.AST.lineno in Python 3.12 docs]
- The class-contract stage (D-13 step 4) is best done POST-import via `inspect` — AST alone cannot resolve inheritance through `import`. The AST stage only checks "at least one class named `Mechanic` in bases"; the import stage then does real `issubclass(cls, Mechanic)`.

### Pattern 3: Validation Pipeline Composition

**What:** Stages are sequential; each stage either passes (continue), hard-fails (accumulate + stop), or emits warnings (accumulate + continue). Implemented as a series of functions each taking `(report, ...)` and mutating it.

**When to use:** Plan 04-02, orchestrating the 6 stages.

**Example sketch:**
```python
def validate(module_path: Path) -> ValidationReport:
    report = ValidationReport(module_path=module_path)

    tree = _stage_syntax(report, module_path)
    if not report.passed:
        return report

    classes_by_name = _stage_ast(report, tree, module_path)
    if not report.passed:
        return report

    module = _stage_import(report, module_path)
    if not report.passed:
        return report

    mechanic_classes = _stage_contract(report, module)
    if not report.passed:
        return report

    _stage_tests(report, module_path, mechanic_classes)
    if not report.passed:
        return report

    _stage_smoke(report, mechanic_classes)

    return report
```

Each stage function is independently unit-testable. Warnings accumulate across stages and are serialized into the report alongside errors.

### Pattern 4: Registry Auto-Scan Caching

**What:** D-15 says registry re-scans `mechanics/` on every `resume_tick`. Naive implementation re-validates every module every tick — expensive. Use `(mtime, size)` as a cache key; skip validation when unchanged.

**When to use:** Plan 04-02, implementing registry auto-scan hook.

**Example:**
```python
@dataclass
class _ScanCacheEntry:
    mtime_ns: int
    size: int
    info: MechanicInfo
    cls: type[Mechanic]

class MechanicRegistry:
    def __init__(self, ...) -> None:
        self._cache: dict[Path, _ScanCacheEntry] = {}
        self.scan()

    def scan(self) -> list[ValidationReport]:
        """Rebuild index; return validation reports for modules that changed.

        Unchanged modules (same mtime_ns + size) reuse the cached class/info.
        """
        reports = []
        seen = set()
        for module_path in discover_mechanic_modules(self._mechanics_dir):
            seen.add(module_path)
            stat = module_path.stat()
            cached = self._cache.get(module_path)
            if cached and cached.mtime_ns == stat.st_mtime_ns and cached.size == stat.st_size:
                continue  # unchanged; reuse cache
            report = validate(module_path)
            reports.append(report)
            if not report.passed:
                self._cache.pop(module_path, None)
                continue
            classes = load_mechanic_classes(module_path)
            for cls in classes:
                info = MechanicInfo(id=cls.id, description=cls.description,
                                    voluntary=cls.voluntary, tags=list(cls.tags), path=module_path)
                self._cache[module_path] = _ScanCacheEntry(
                    mtime_ns=stat.st_mtime_ns, size=stat.st_size, info=info, cls=cls,
                )
        # Evict deleted modules
        for path in list(self._cache):
            if path not in seen:
                del self._cache[path]
        self._rebuild_index_from_cache()
        return reports
```

**Rationale:** mtime_ns + size is a cheap, sufficient invalidation signal for v1. Content hash is overkill and costly; importlib reload semantics (`importlib.reload`) are fragile for classes with subclass hierarchies. Do NOT use `importlib.reload`. [ASSUMED: mtime_ns resolution on all supported platforms — Linux/macOS provide nanoseconds, Windows NTFS is ~100ns; confirm before commit]

### Pattern 5: Diagnostics Filesystem Schema & Sink

**What:** `DiagnosticsSink` owns the `universe/diagnostics/` root; exposes `open_tick(tick_id)` returning a `TickDiagnostics` context object.

**When to use:** Plan 04-03, new `mechanic/diagnostics.py`.

**Example:**
```python
# src/token_world/mechanic/diagnostics.py
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1


class DiagnosticsSink:
    """Filesystem substrate for per-tick diagnostics (AUTO-02).

    Owns `<universe>/diagnostics/`. Creates subfolders on demand; never deletes.
    """

    def __init__(self, universe_dir: Path) -> None:
        self._root = universe_dir / "diagnostics"
        self._root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def open_tick(self, tick_id: int) -> Iterator[TickDiagnostics]:
        """Context manager: creates tick_<id>/, yields ctx, writes summary.json on close."""
        tick_dir = self._root / f"tick_{tick_id}"
        tick_dir.mkdir(exist_ok=True)
        ctx = TickDiagnostics(tick_dir=tick_dir, tick_id=tick_id)
        try:
            yield ctx
        finally:
            ctx.finalize()

    def open_validation(self, mechanic_id: str) -> Path:
        """Create and return a validation/<timestamp>_<id>/ folder."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_id = mechanic_id.replace("/", "_")
        d = self._root / "validation" / f"{ts}_{safe_id}"
        d.mkdir(parents=True, exist_ok=True)
        return d


class TickDiagnostics:
    """Per-tick diagnostics context. Created by DiagnosticsSink.open_tick()."""

    def __init__(self, tick_dir: Path, tick_id: int) -> None:
        self._dir = tick_dir
        self._tick_id = tick_id
        self._summary: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "tick_id": tick_id,
            "status": "pending",
        }

    def write_action(self, text: str) -> None:
        (self._dir / "action.txt").write_text(text, encoding="utf-8")

    def write_classification(self, *, prompt: str, response: str, parsed: dict) -> None:
        d = self._dir / "classification"
        d.mkdir(exist_ok=True)
        (d / "prompt.txt").write_text(prompt, encoding="utf-8")
        (d / "response.txt").write_text(response, encoding="utf-8")
        _atomic_write_json(d / "parsed.json", parsed)

    def append_mutation(self, mutation_dict: dict) -> None:
        d = self._dir / "execution"
        d.mkdir(exist_ok=True)
        # JSON-lines append (NOT atomic — per-line duplicates on crash are acceptable)
        with (d / "mutations.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(mutation_dict) + "\n")

    def set_summary(self, **fields: Any) -> None:
        self._summary.update(fields)

    def finalize(self) -> None:
        self._summary.setdefault("status", "ok")
        _atomic_write_json(self._dir / "summary.json", self._summary)


def _atomic_write_json(path: Path, obj: Any) -> None:
    """Write JSON atomically: tmp file in same dir + os.replace."""
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, prefix=path.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

**Key choices:**
- `os.replace` is atomic on both POSIX and Windows. [VERIFIED: docs.python.org/3/library/os.html#os.replace]
- `mutations.jsonl` is append-only; per-line is the unit of consistency. A crash mid-tick may leave a partial JSON line; reader should tolerate this. Alternative: write all mutations into a temp file then `os.replace` to `mutations.jsonl` at `finalize()` — but that loses mid-tick visibility for debugging.
- Summary is written atomically once at `finalize()` — this is the tick's "commit point".
- Schema version is `1` for all v1 outputs. Future readers check `summary["schema_version"]` before parsing.

### Pattern 6: Integration Test Harness

**What:** Load all 35 use-case manifests at module import; parametrize a single test function across them with per-case markers indicating expected outcome.

**When to use:** Plan 04-04, new `tests/test_integration/test_use_cases.py`.

**Example:**
```python
# tests/test_integration/test_use_cases.py
from __future__ import annotations

from pathlib import Path
import pytest

from token_world.use_cases import load_use_case

USE_CASES_DIR = Path(__file__).resolve().parents[2] / ".planning" / "use-cases"
CATEGORIES = ["spatial", "social", "resource", "environmental", "edge-case"]


def _discover_cases() -> list[pytest.param]:
    params = []
    for category in CATEGORIES:
        cat_dir = USE_CASES_DIR / category
        if not cat_dir.is_dir():
            continue
        for path in sorted(cat_dir.glob("UC-*.md")):
            fm, _body = load_use_case(path)
            uc_id = fm["id"]
            marks = []
            # D-29b outcome coding
            if _is_blocked_by_framework_gap(fm):
                marks.append(pytest.mark.skip(reason=f"blocked by framework gap: {_blocking_gap(fm)}"))
            elif _is_yield_expected(fm):
                marks.append(pytest.mark.xfail(reason="no matching mechanic (yield)", strict=False))
            params.append(pytest.param(path, id=uc_id, marks=marks))
    return params


@pytest.mark.parametrize("use_case_path", _discover_cases())
def test_use_case(use_case_path: Path, kg_builder) -> None:
    fm, _ = load_use_case(use_case_path)
    # 1. Build graph via setup.graph_builder
    kg = kg_builder()
    exec(compile(fm["setup"]["graph_builder"], str(use_case_path), "exec"), {"kg": kg})
    # 2. Invoke chain execution for each action
    # 3. Assert expected_observations[].graph_assertions
    ...
```

**Marking logic:**
- `_is_blocked_by_framework_gap`: scan `fm["gaps"]` — if any gap has `layer=="engine"` + `severity=="address-now"` + matches known framework gaps (GAP-ENG03, GAP-ENG05, etc.), skip with that gap's ID.
- `_is_yield_expected`: fm declares "no matching mechanic" via a convention the planner picks — recommend adding a `fm["expected_outcome"]` field OR deriving from whether any `expected_observations[*].narrative_contains` is empty. NEEDS PLANNER DECISION (see Open Questions).
- `pytest.mark.xfail(strict=False)` — yield cases are expected to fail today but MAY pass once seeds are authored; `strict=False` avoids XPASS failures.

**Parametrize at module load time**, NOT inside a fixture — pytest IDs must be known when the collection phase runs. `load_use_case(path)` is fast enough (tens of ms per file) for 35 files.

[CITED: pytest parametrize with marks: docs.pytest.org/en/stable/how-to/parametrize.html#pytest-mark-parametrize]

### Pattern 7: CLI Commands — validate-mechanic, scaffold-mechanic, prune-diagnostics

**What:** All three extend the existing `@cli.group()` at `src/token_world/cli.py:10`. Pattern is identical to existing commands (`list-mechanics`, `run-mechanic`, `query-graph`).

**When to use:** Plans 04-02 (validate-mechanic), 04-05 (scaffold-mechanic), 04-03 (prune-diagnostics).

**Example — `scaffold-mechanic`:**
```python
@cli.command("scaffold-mechanic")
@click.argument("universe")
@click.option("--id", "mechanic_id", required=True, help="Unique mechanic id")
@click.option("--voluntary/--involuntary", default=True)
@click.option("--description", default="TODO: describe this mechanic")
def scaffold_mechanic(universe: str, mechanic_id: str, voluntary: bool, description: str) -> None:
    manager = UniverseManager()
    universe_dir = manager.load(universe)
    module_path = universe_dir / "mechanics" / f"{mechanic_id}.py"
    test_path = universe_dir / "tests" / "test_mechanics" / f"test_{mechanic_id}.py"
    if module_path.exists():
        click.echo(f"Error: {module_path} already exists", err=True)
        raise SystemExit(1)
    module_path.write_text(_render_mechanic_skeleton(mechanic_id, voluntary, description))
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(_render_test_skeleton(mechanic_id))
    click.echo(f"Scaffolded {module_path} and {test_path}")
```

**Prefer plain f-strings** over Jinja2 for these skeletons — the templates are ~20 lines each, and the universe CLAUDE.md template already uses `string.Template` (`templates/claude_md.py`). Adding Jinja2 for two one-off skeletons is overkill.

### Anti-Patterns to Avoid

- **`importlib.reload()` in the registry cache path.** It does not reliably reload class hierarchies and breaks `issubclass` checks across sessions. Drop the cache entry and re-import fresh.
- **`ast.literal_eval` on user-provided test data.** Not used in Phase 4 but tempting for the smoke stage. Instead, construct a minimal `KnowledgeGraph` + `MechanicContext` with a claimable actor/target and call `check()`.
- **Walrus-operator parsing tricks in AST rules.** Keep the visitor linear: one rule per `visit_*` method. Testability > cleverness.
- **Absolute paths in `summary.json`.** Store paths relative to `universe_dir` so diagnostics folders are portable/archivable.
- **Writing `summary.json` per-mutation.** Only write at `finalize()`. Appending is reserved for `mutations.jsonl`.
- **Using `shutil.copytree(..., dirs_exist_ok=True)` in the new scaffold.** Flat copy should iterate individual `.py` files, not copy a tree — the old tree included `tests/` subfolders that no longer exist in the flat layout.
- **Raising on the first AST finding.** D-13 says "stop at first hard-failing stage, accumulate all findings within that stage". The AST stage MUST walk the entire tree and accumulate every forbidden import/call before returning.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python source parsing | String-based regex for `from networkx import ...` | `ast.parse` + `ast.NodeVisitor` | Regex misses multi-line imports, string-literal false positives, conditional imports inside try/except. AST is exact. |
| Atomic file write | Custom lockfile / try-write-on-fail | `tempfile.mkstemp(dir=parent) + os.replace` | POSIX+Windows atomic rename is a decades-stable primitive. [VERIFIED: docs] |
| YAML frontmatter parsing | Hand-rolled splitter | Existing `use_cases/loader.py` (fix CRLF, consume directly) | Phase 3 already built and tested this. Re-implementing violates D-28. |
| pytest parametrize IDs | Dynamic test generation via `pytest_generate_tests` | `@pytest.mark.parametrize("path", [pytest.param(p, id="UC-S01")])` at module level | Module-level params generate test IDs visible in `pytest --collect-only` and in CI logs. |
| Git history walking | Custom `git log` parsing | Existing `MechanicRegistry.get_history` (already works for folders; repoint to files) | Change one line: `info.path` is now a file, not a directory; `git log -- <file>` is identical to `git log -- <folder>`. |
| Mechanic introspection | `ast.parse` + name matching | After successful import, `issubclass(cls, Mechanic)` + `inspect.signature(cls.check)` | AST knows names, not types. Real subclass checks require runtime resolution. Stage-2 AST is a fast gate; stage-4 contract does the rigorous check. |
| Timestamp formatting | Ad-hoc format strings | `datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")` | ISO-8601 basic format is filesystem-safe (no colons). |
| Mutation serialization | `json.dumps(mutation.__dict__)` | `json.dumps(dataclasses.asdict(mutation))` | Handles nested dataclasses + is schema-transparent. |

**Key insight:** Phase 4 is dense with "compose stdlib primitives" problems. Every instinct to reach for a library should be checked — Python 3.12 stdlib covers all six deliverables.

## Common Pitfalls

### Pitfall 1: AST Stage Missing Transitive Mechanic Subclasses

**What goes wrong:** A mechanic module defines `class MyThing(SpatialMechanic): ...` where `SpatialMechanic(Mechanic)` is imported from `_helpers.py`. AST-only check for `bases.id == "Mechanic"` misses it.

**Why it happens:** AST cannot resolve `import` — it only sees names. `SpatialMechanic` is an `ast.Name("SpatialMechanic")` in bases, not `Mechanic`.

**How to avoid:** Treat the AST stage's `no_mechanic_subclass` rule as a **warning**, not an error. The real `issubclass` check happens at stage 4 (class contract) after `import`. If AST finds zero classes with `Mechanic` in bases, warn but continue; stage 4 catches the truly broken case.

**Warning signs:** A legitimate `SpatialMechanic`-based mechanic failing validation at the AST stage.

### Pitfall 2: Stale Cache After External Git Checkout

**What goes wrong:** Operator does `git checkout <branch>` that rewrites `mechanics/movement.py` with an older mtime (common with certain git configs). Cache key `(mtime, size)` reports unchanged; registry serves stale class.

**Why it happens:** Git preserves original file timestamps when checking out old commits; mtime_ns can go backward or stay identical to a previously-cached version.

**How to avoid:** Use `(mtime_ns, size, sha256_digest_of_first_4KB)` as the cache key. Hashing only the first 4KB keeps it cheap; mechanic modules are almost never >4KB. OR: clear the cache wholesale on `resume_tick` if the plan doesn't care about cache hit rate — D-15 says scan every tick anyway.

**Warning signs:** "Why is my edit not taking effect?" — operator reports mismatched behavior.

### Pitfall 3: Use-Case Harness Swallows Errors from Graph Builder

**What goes wrong:** A use-case manifest's `setup.graph_builder` contains a typo (`kg.ad_node(...)`). `exec(...)` raises `AttributeError` mid-test. Pytest reports the test as failed, not as "use case is malformed" — muddles the signal.

**Why it happens:** Raw `exec` bubbles exceptions into test failure.

**How to avoid:** Wrap `exec` in a try/except that catches any exception and re-raises as `pytest.fail(f"UC-{id} setup.graph_builder is invalid: {e}")`. Alternative: pre-validate all manifests at module-load time and skip the invalid ones with a clear reason.

**Warning signs:** Cryptic `AttributeError` traces in the integration harness; a specific use case suddenly fails after unrelated edits.

### Pitfall 4: register_mechanic Reference Leakage

**What goes wrong:** Plan 04-01 drops `register_mechanic` from `mcp_server.py` and `templates/claude_md.py` but misses references in verification docs, older plan artifacts, or a test helper. MCP stub server serves 3 tools; a test still expects 4 and fails.

**Why it happens:** The string appears in 13 files (per grep). Some are docs; some are tests.

**How to avoid:** Grep `register_mechanic` BEFORE and AFTER the change. Update the two operational files (`mcp_server.py`, `templates/claude_md.py`) and the two tests (`tests/test_mcp_server.py`, `tests/test_universe/test_scaffold.py`). Explicitly mark all `.planning/phases/00-*/` docs as historical — do NOT rewrite history. [VERIFIED: grep shows 13 files; 4 are active code/tests; 9 are planning/phase docs]

**Warning signs:** `pytest tests/test_mcp_server.py` or `tests/test_universe/test_scaffold.py` failures after plan 04-01.

### Pitfall 5: Seed Tests Not Migrating Cleanly

**What goes wrong:** Current seed tests live under `tests/test_mechanic/test_seed_movement.py` (flat under `test_mechanic/`). D-06 says they should move to `tests/test_mechanic/test_seeds/test_movement.py`. Simple `git mv` works, but the test files currently import seed modules via `from token_world.mechanic.seeds.movement.mechanic import MovementMechanic` — that path no longer exists.

**Why it happens:** Flattening changes the import path from `seeds.movement.mechanic` to `seeds.movement`.

**How to avoid:** After the `git mv`, grep-replace imports: `from token_world.mechanic.seeds.movement.mechanic` → `from token_world.mechanic.seeds.movement`. Run `uv run pytest tests/test_mechanic/test_seeds/ -x -q` immediately after move. Plan 04-01 should explicitly include this rename as a verified step.

**Warning signs:** `ImportError: cannot import name 'MovementMechanic'` in the test run immediately after plan 04-01.

### Pitfall 6: Frozen DSL Blocks Framework-Gap Stubs

**What goes wrong:** MECH12 declares it needs `actors: list[NodeId]` + `sum_property(...)` on `MechanicContext`. The stub mechanic tries to import a symbol that doesn't exist; AST validation passes (not forbidden) but import fails with `ImportError`.

**Why it happens:** Stubs for framework-gap-blocked mechanics need to represent "I depend on X" without importing X.

**How to avoid:** Convention (to be documented in authoring guide per D-30): stub mechanics declare their gap via a class-level attribute, and their `check()` returns `CheckResult(passed=False, reasons=["blocked by GAP-ENG05 until Phase 5"])`. They never import a symbol that doesn't exist.

```python
class CooperateMechanic(Mechanic):
    id = "cooperate"
    description = "Multi-actor lifting (MECH12; blocked on GAP-ENG05)"
    voluntary = True
    blocked_by = "GAP-ENG05"

    def check(self, ctx: MechanicContext) -> CheckResult:
        return CheckResult(passed=False, reasons=[f"blocked by framework gap {self.blocked_by}"])

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return []
```

The integration harness reads `blocked_by` via `getattr(cls, "blocked_by", None)` to decide the marker.

**Warning signs:** Framework-gap stub fails validation stage 3 (import) with an undefined-name error.

### Pitfall 7: H-01 Fix Masks a Deeper Invariant

**What goes wrong:** H-01 patch adds `elif e.event_type == "add_node": state = json.loads(e.new_value_json) or {}`. But subsequent `set_property` events after the add_node are supposed to modify the state; the new branch resets it. Correct behavior: add_node should REPLACE current state with the payload (not reset to empty), then subsequent set_property events refine it.

**Why it happens:** The 03-REVIEW.md fix suggests `state = json.loads(...)`, which is correct — but only if subsequent loop iterations continue to update `state` in-place.

**How to avoid:** The current code at `temporal.py:151` has `elif e.event_type in ("remove_node", "add_node"): state = {}` — both reset. The fix splits this: `add_node` seeds from payload, `remove_node` clears. Regression test must cover: add → set → remove → add → set → query (state reflects both adds and the final set). [VERIFIED: review file lines 71-76]

**Warning signs:** The regression test in plan 04-01 only covers add → remove → add and misses the interleaved set_property case.

## Runtime State Inventory

Phase 4 is NOT purely greenfield — it rewrites loader/registry and flattens seed folders. Running state matters.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | None — graph databases hold node/edge data keyed by universe-authored IDs, not by mechanic `id`. Mechanic IDs appear in event payloads (`ExecutionTrace` serialization) but existing universes would not yet contain any (Phase 4 is the first phase to run a simulation). [VERIFIED: `find ~/.local/share/token_world/universes 2>&1` — directory does not exist; no existing universes] | None |
| **Live service config** | None — no external service stores mechanic names. MCP tool list is baked into `mcp_server.py` (code, not config). | None |
| **OS-registered state** | None — no Task Scheduler, systemd, launchd, or pm2 entries. Project is a library + CLI. | None |
| **Secrets/env vars** | None — no environment variable references the mechanic layout. `ANTHROPIC_API_KEY` is for Phase 5/6. | None |
| **Build artifacts** | `src/token_world/mechanic/seeds/movement/__pycache__/`, `seeds/observation/__pycache__/`, `seeds/environmental_reaction/__pycache__/`. After flattening, these become stale but harmless. [VERIFIED: `ls` output shows `__pycache__/` in every seed folder] | Plan 04-01 should `rm -rf src/token_world/mechanic/seeds/*/__pycache__` after removing the folders, or rely on the folder deletion to take the `__pycache__` with it. `find . -name __pycache__ -exec rm -rf {} +` as a post-step is fine. |

**Historical planning artifacts:** `.planning/phases/00-universe-infrastructure/*.md` mention `register_mechanic`. These are historical records and must NOT be rewritten. They reflect the state of the project AT that phase; superseded decisions are recorded in the SUPERSEDED note pattern already established in `02-CONTEXT.md` D-15/D-16. Plan 04-01 should append a matching note to the relevant Phase 0 docs IF it rewrites them; otherwise leave as-is. [VERIFIED: grep of 13 files]

## Code Examples

### Example 1: Fixing H-01 in temporal.py

```python
# src/token_world/graph/temporal.py:146-153 (CURRENT)
for e in history:
    if e.event_type == "set_property" and e.property_name:
        state[e.property_name] = (
            json.loads(e.new_value_json) if e.new_value_json is not None else None
        )
    elif e.event_type in ("remove_node", "add_node"):
        state = {}

# FIXED (per 03-REVIEW.md lines 71-76)
for e in history:
    if e.event_type == "set_property" and e.property_name:
        state[e.property_name] = (
            json.loads(e.new_value_json) if e.new_value_json is not None else None
        )
    elif e.event_type == "add_node":
        # Seed state from the add_node payload; subsequent set_property
        # events in the same loop continue to refine it.
        state = json.loads(e.new_value_json) if e.new_value_json else {}
    elif e.event_type == "remove_node":
        state = {}
```

Regression test (add to `tests/test_graph/test_temporal_index.py`):
```python
def test_find_state_at_tick_handles_remove_then_readd(kg: KnowledgeGraph) -> None:
    # Tick 0: add node with props
    kg.add_node("apple", node_type="entity", color="red", weight=1)
    # Tick 1: snapshot
    kg.snapshot(summary="after-add")
    # Tick 2: remove
    kg.remove_node("apple")
    # Tick 3: re-add with different props
    kg.add_node("apple", node_type="entity", color="green", weight=2)
    # Tick 4: modify
    kg.set("apple", "weight", 3)

    ti = TemporalIndex(kg)
    state = ti.find_state_at_tick("apple", tick_id=4)
    assert state["color"] == "green"
    assert state["weight"] == 3
```

### Example 2: M-04 CRLF fix in use_cases/loader.py

```python
# src/token_world/use_cases/loader.py:35 (CURRENT)
text = path.read_text(encoding="utf-8")
if not text.startswith("---\n"):
    raise ValueError(f"{path}: missing YAML frontmatter")
parts = text.split("---\n", 2)

# FIXED
text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
if not text.startswith("---\n"):
    raise ValueError(f"{path}: missing YAML frontmatter")
parts = text.split("---\n", 2)
```

Regression test: write a fixture with `\r\n` delimiters and assert it loads identically to the `\n` version.

### Example 3: Updated mcp_server.py TOOLS

```python
# src/token_world/mcp_server.py:16 (CURRENT — 4 tools)
TOOLS = [
    {"name": "resume_tick", ...},
    {"name": "rollback", ...},
    {"name": "list_mechanics", ...},
    {"name": "register_mechanic", "description": "Register a new mechanic from a mechanics/ subfolder", ...},  # DROP
]

# FIXED — 3 tools (D-19)
TOOLS = [
    {"name": "resume_tick", ...},
    {"name": "rollback", ...},
    {"name": "list_mechanics", ...},
]
```

Test update: `tests/test_mcp_server.py:42` changes `{"resume_tick", "rollback", "list_mechanics", "register_mechanic"}` to `{"resume_tick", "rollback", "list_mechanics"}`; delete the `test_register_mechanic_requires_path` method.

### Example 4: Seed mechanic template (for scaffold-mechanic)

```python
# Template for scaffold-mechanic output
_MECHANIC_TEMPLATE = '''"""{description}"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


class {class_name}(Mechanic):
    """{description}

    Preconditions:
        - TODO

    Side effects:
        - TODO
    """

    id = "{mechanic_id}"
    description = "{description}"
    voluntary = {voluntary}
    tags: list[str] = []

    def check(self, ctx: "MechanicContext") -> CheckResult:
        # TODO: implement preconditions
        return CheckResult(passed=False, reasons=["TODO: implement check"])

    def apply(self, ctx: "MechanicContext") -> list[Mutation]:
        # TODO: implement side effects
        return []
'''
```

### Example 5: MECH01 (passage_move) — concrete seed sketch

From GAP-MECH01: movement seed traverses `connects` without inspecting intermediate blocking entities. Implementation sketch:

```python
# src/token_world/mechanic/seeds/passage_move.py
class PassageMoveMechanic(Mechanic):
    id = "passage_move"
    description = "Agent moves through a passage entity (doorway) if it is open"
    voluntary = True
    tags: list[str] = ["spatial", "passage"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor) or not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["actor or target missing"])
        actor_loc = ctx.query_node(ctx.actor).get("location")
        if not actor_loc:
            return CheckResult(passed=False, reasons=["actor has no location"])
        # Find a passage entity connecting actor_loc to ctx.target
        passage = _find_open_passage(ctx, src=actor_loc, dst=ctx.target)
        if passage is None:
            return CheckResult(passed=False, reasons=["no open passage to target"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.actor, "location", ctx.target)]
```

`_find_open_passage` lives in `seeds/_helpers.py` — shared with MECH27 (`try_door`) and MECH05 (terrain). This is the right place to grow `_helpers.py` organically per D-11.

## State of the Art

| Old Approach (Phase 2) | Current Approach (Phase 4) | When Changed | Impact |
|--------------------|----------------------|--------------|--------|
| Folder-per-mechanic with `mechanic.py` + `meta.yaml` + `tests/` | Flat `<id>.py` modules; class attributes; tests in mirrored project test tree | 2026-04-12 (this phase) | Simpler git history (`git log -- mechanics/x.py`); no YAML parsing in registry; scaffold-mechanic emits one file |
| 4-tool MCP surface (`resume_tick`, `rollback`, `list_mechanics`, `register_mechanic`) | 3-tool surface (drop `register_mechanic`) | 2026-04-12 | Universe = codebase; "registration" = "file exists and passes validation" |
| `MechanicRegistry` scans folders once at init; no auto-revalidation | Auto-scan on every `resume_tick` with mtime-based cache | 2026-04-12 | Operator edits take effect at next tick without explicit reload |

**Deprecated/outdated:**
- `meta.yaml` — class attributes are authoritative.
- `mechanic.py` filename convention inside a folder — replaced by `<id>.py` at top level.
- `register_mechanic` MCP tool — dropped entirely.
- `source='llm_generated'` / `reviewed` fields on mechanics (GAP-MECH19 original framing) — obsolete per D-35; validation gate runs on every mechanic regardless of origin.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | mtime_ns resolution is adequate for cache invalidation on all supported platforms (Linux, macOS, Windows NTFS). | Pattern 4 — Registry Auto-Scan Caching | Stale cache after same-second edit. Mitigation: include first-4KB SHA-256 in cache key. |
| A2 | `pytest 7.0.0` is the actual installed version despite pyproject declaring `pytest>=9.0`. Plans should target `>=8.0` behavior (parametrize + marks). | Standard Stack | Low — parametrize-with-marks has been stable since pytest 4.x. |
| A3 | Bandit/pylint plugin APIs are heavier than a custom `ast.NodeVisitor` for 5-10 rules. | Alternatives Considered | If scope grows to 20+ rules, a bandit plugin may be easier — revisit at plan 04-02. |
| A4 | Ruff plugin API is still limited as of 2026-04 — not suitable for custom repo-specific rules. | Alternatives Considered | If Ruff adds stable plugin support, a future phase could replace the custom visitor. Not a v1 concern. |
| A5 | `os.replace` guarantees atomic rename on Windows in Python 3.12 (since Python 3.3). | Pattern 5 — Diagnostics | None — well-documented stdlib behavior. [Actually VERIFIED via docs, upgrade this row to `[CITED]`] |
| A6 | No existing universe folders on the operator machine. `~/.local/share/token_world/universes/` is empty. | Runtime State Inventory | Low — if universes exist with Phase 2/3 folder-structured mechanics, plan 04-01 must include a migration helper `flatten-universe-mechanics <universe>` that reshapes `mechanics/<id>/mechanic.py` → `mechanics/<id>.py` + deletes stale subfolders. VERIFY BEFORE PLAN 04-01 by `ls ~/.local/share/token_world/universes/`. |
| A7 | The registry does not need to re-scan on EVERY file-read op — just at `resume_tick` boundaries (D-15). Plan can expose `registry.scan()` to be called explicitly. | Pattern 4 | If Phase 5 needs more granular invalidation, revisit. |
| A8 | Framework-gap-blocked stubs (MECH09, MECH12) should NOT exercise the full integration harness — their `check()` returns `passed=False`, so the harness naturally sees a "check failed" outcome that matches the "blocked" marker. | Pitfall 6 | If the harness distinguishes "blocked" from "check failed with a reason", add an explicit `blocked_by` convention. Planner decides. |
| A9 | `yield` use cases are distinguishable from pass/fail by `fm["gaps"]` content — if all gaps have `severity=="address-now"` and the matching seed mechanic does not exist yet, it's a yield. | Pattern 6 — Integration Harness | Requires a concrete mapping rule. Planner may prefer adding an explicit `expected_outcome: "yield"|"pass"|"blocked"|"fail"` field to the manifest. Revisit in discuss for plan 04-04. |
| A10 | 27 seed mechanics can fit in 4-7 thematic clusters with minimal shared state. | Wave Parallelism | Some clusters may need serialization if they share `_helpers.py` additions; suggest per-cluster serial within cluster, parallel across clusters. |

## Open Questions

1. **How does the integration harness distinguish "yield" from "fail" per D-29b?**
   - What we know: D-29b names four outcomes (pass / yield / blocked-by-framework-gap / fail). Manifests have `fm["gaps"]` listing gap IDs and severities.
   - What's unclear: There's no `expected_outcome` field in the manifest schema (REQUIRED_KEYS in `use_cases/loader.py:11` doesn't include it).
   - Recommendation: Plan 04-04 adds an OPTIONAL `expected_outcome` frontmatter field OR derives the outcome from existing fields (e.g., "if all seed mechanics the UC depends on exist → pass; if any cite an engine-layer gap → blocked; else yield"). Discuss in plan 04-04 pre-work.

2. **Does the scaffold-mechanic test stub default to full test or skeleton?**
   - CONTEXT.md D-32 explicitly leaves this to Claude's discretion.
   - Recommendation: Plan 04-05 emits a fully executable stub that asserts `CheckResult(passed=False)` — this keeps pytest green when the skeleton is first generated, so the operator iterates forward rather than starting from a red bar.

3. **Should `_helpers.py` be scaffolded empty or omitted?**
   - D-05 says helpers live as `_*.py`; D-09 says "empty at first; for shared utilities as duplication emerges".
   - Recommendation: Create `_helpers.py` as an empty file so the file exists and operators notice its presence. Zero-byte files cost nothing.

4. **What pytest version does the project actually support?**
   - `pyproject.toml` says `>=9.0`, local env has `7.0.0`. Plan 04-04 should verify with `uv run pytest --version` before relying on pytest-9-specific features. Recommend sticking to pytest-7-compatible API (parametrize + marks + xfail) to avoid surprises.

5. **Does `scaffold-mechanic` need to run INSIDE the universe's venv, or from the installed token-world?**
   - Universes don't have their own venv; tests run from the project root. Scaffold output is static Python + a test file. Both files import `token_world.mechanic.protocol` which requires the project to be installed (`uv sync` before running). Document this in 04-05.

6. **Authoring-guide (`docs/guides/authoring-mechanics.md`) length — how much?**
   - D-30 lists: class contract, DSL reference, common patterns, anti-patterns, worked examples. Estimate: 400-800 lines covering the 3 seed patterns + framework-gap-stub pattern + `_helpers.py` convention + test conventions.
   - Recommendation: Plan 04-05 targets 500-600 lines; long enough to be a real reference, short enough to re-read in a single session.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything | ✓ | 3.12.12 | — |
| uv | Package + test running | ✓ | 0.9.24 | — |
| pytest | D-13 stage 5 + integration harness | ✓ | 7.0.0 (pyproject declares ≥9.0) | — — use pytest-7-compatible API |
| git | Mechanic history (D-08) | ✓ (used in `registry.py:186`) | — | Skip history gracefully per existing `FileNotFoundError` handling |
| networkx | Graph (indirect only for mechanics) | ✓ | 3.6+ | — |
| Anthropic SDK | Phase 5/6 only | ✓ (installed per pyproject) | 0.80+ | N/A for Phase 4 |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.0.0 installed locally; pyproject declares `>=9.0`. Plans target pytest-7+compatible API. |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` sets `testpaths=["tests"]`, `pythonpath=["src"]`. |
| Quick run command | `uv run pytest -x -q` |
| Full suite command | `uv run pytest -v` |
| Lint | `uv run ruff check src/` |
| Format check | `uv run ruff format --check src/` |
| Type check | `uv run mypy src/token_world/mechanic/` (extend to new modules) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MECH-03 | Operator-authored mechanic passes validation end-to-end | integration | `uv run pytest tests/test_integration/test_use_cases.py -x -q` | ❌ Wave 0 (created by 04-04) |
| MECH-04 | Syntax-bad module fails stage 1 | unit | `uv run pytest tests/test_mechanic/test_validation.py::test_syntax_error -x` | ❌ Wave 0 (04-02) |
| MECH-04 | Forbidden import triggers AST rule | unit | `uv run pytest tests/test_mechanic/test_validation.py::test_forbidden_import_networkx -x` | ❌ Wave 0 (04-02) |
| MECH-04 | Forbidden `eval` call triggers AST rule | unit | `uv run pytest tests/test_mechanic/test_validation.py::test_forbidden_call_eval -x` | ❌ Wave 0 (04-02) |
| MECH-04 | Missing `id` class attr fails contract stage | unit | `uv run pytest tests/test_mechanic/test_validation.py::test_missing_id_attr -x` | ❌ Wave 0 (04-02) |
| MECH-04 | Invalid mechanic is excluded from registry; report written to diagnostics | integration | `uv run pytest tests/test_mechanic/test_registry.py::test_invalid_mechanic_excluded -x` | ❌ Wave 0 (04-02) |
| MECH-05 | Registry discovers `<id>.py` flat modules | unit | `uv run pytest tests/test_mechanic/test_registry.py::test_flat_discovery -x` | ❌ Wave 0 (04-01) |
| MECH-05 | Registry skips `_helpers.py` | unit | `uv run pytest tests/test_mechanic/test_registry.py::test_skips_underscore_modules -x` | ❌ Wave 0 (04-01) |
| MECH-06 | Tag query returns matching mechanics | unit | `uv run pytest tests/test_mechanic/test_registry.py::test_query_by_tag -x` | ✓ exists; may need update |
| TEST-02 | Use-case manifest exercises multi-mechanic chain | integration | `uv run pytest tests/test_integration/test_use_cases.py::test_use_case[UC-S01] -x` | ❌ Wave 0 (04-04) |
| TEST-02 | Framework-gap-blocked UC is skipped with reason | integration | `uv run pytest tests/test_integration/test_use_cases.py::test_use_case[UC-O06] -x` (expects SKIP) | ❌ Wave 0 (04-04) |
| AUTO-02 | DiagnosticsSink writes atomic `summary.json` | unit | `uv run pytest tests/test_mechanic/test_diagnostics.py::test_atomic_summary_write -x` | ❌ Wave 0 (04-03) |
| AUTO-02 | DiagnosticsSink tolerates partial mutations.jsonl on crash | unit | `uv run pytest tests/test_mechanic/test_diagnostics.py::test_partial_mutations_line -x` | ❌ Wave 0 (04-03) |
| AUTO-02 | prune-diagnostics removes tick folders older than cutoff | unit | `uv run pytest tests/test_cli/test_prune_diagnostics.py -x` | ❌ Wave 0 (04-03) |
| UNIV-03 | MCP stub server exposes exactly 3 tools | unit | `uv run pytest tests/test_mcp_server.py -x` | ✓ exists; MUST UPDATE (drop `register_mechanic`) |
| H-01 (prereq) | `find_state_at_tick` replays add_node after remove | unit | `uv run pytest tests/test_graph/test_temporal_index.py::test_remove_then_readd -x` | ❌ Wave 0 (04-01) |
| M-04 (prereq) | Use-case loader accepts CRLF frontmatter | unit | `uv run pytest tests/test_design_validation/test_use_case_schema.py::test_crlf_frontmatter -x` | ❌ Wave 0 (04-01) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_mechanic/ tests/test_cli/ -x -q` (quick feedback; ~seconds)
- **Per wave merge:** `uv run pytest -x -q` (full suite including integration)
- **Phase gate:** `uv run pytest -v` + `uv run ruff check src/` + `uv run ruff format --check src/` + `uv run mypy src/token_world/` all green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_mechanic/test_validation.py` — covers MECH-04 stages and each AST rule
- [ ] `tests/test_mechanic/test_diagnostics.py` — covers AUTO-02 sink lifecycle + atomic writes
- [ ] `tests/test_mechanic/test_seeds/` directory — D-06 mirrored layout; migrate existing seed tests
- [ ] `tests/test_integration/test_use_cases.py` — parametrized harness (TEST-02)
- [ ] `tests/test_cli/test_validate_mechanic.py`, `test_scaffold_mechanic.py`, `test_prune_diagnostics.py`
- [ ] `tests/test_graph/test_temporal_index.py::test_remove_then_readd` — H-01 regression
- [ ] `tests/test_design_validation/test_use_case_schema.py::test_crlf_frontmatter` — M-04 regression

No framework install needed — pytest is already configured.

## Security Domain

Security enforcement is enabled (config.json shows no `security_enforcement: false`). However, Phase 4 is a low-risk phase: no network I/O, no secrets, no authentication. The only security-relevant surface is the validation pipeline itself.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V1 Architecture | yes | AST rules are a **defense-in-depth**, not a security boundary. Explicit statement in authoring guide. |
| V2 Authentication | no | Local CLI; no auth surface |
| V3 Session Management | no | No sessions in Phase 4 |
| V4 Access Control | no | Single-user universe model |
| V5 Input Validation | yes | Use-case manifest validation (already in `use_cases/loader.py`); mechanic source validation (Phase 4 new). Pydantic-style defensive checks on every boundary. |
| V6 Cryptography | no | No crypto in Phase 4 |
| V7 Errors & Logging | yes | ValidationReport findings include file:line:column; diagnostics use structured JSON; no PII/secret exposure |
| V8 Data Protection | no | No sensitive data in diagnostics (prompts + LLM responses are simulation content, not user secrets) |
| V10 Malicious Code | partially | Mechanics ARE code the operator writes. AST rules catch obvious foot-guns (eval, __import__); full defense requires RestrictedPython (deferred to v2) |
| V12 File Handling | yes | `prune-diagnostics` walks filesystem — MUST not follow symlinks outside universe dir (see known threats) |
| V14 Config | no | No config in Phase 4 |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious mechanic module executes arbitrary code on import (e.g., `os.system("rm -rf ~")` at module top level) | Elevation of Privilege | **Acknowledge:** v1 does NOT mitigate this — no sandboxing per CLAUDE.md. AST rules catch `exec`/`eval`/bare `open` but NOT `os.system` (that would be a `subprocess`/`os` import rule — consider adding). Document as known limitation in authoring guide. |
| YAML deserialization exploit in use-case loader | Tampering | Already mitigated — `use_cases/loader.py` uses `yaml.safe_load` (verified in 03-REVIEW.md). |
| AST parsing DoS via deeply nested Python source | DoS | Python's `ast.parse` has default recursion limit handling; a pathological mechanic that hangs the parser would also break the operator's own editor. Not a v1 concern. |
| Path traversal in `prune-diagnostics --before-tick N` (e.g., `N=../../etc`) | Tampering | `click.IntRange` on `--before-tick`; resolve universe dir via `UniverseManager.load(slug)` which enforces slug validity. |
| Symlink escape in `prune-diagnostics` walking `diagnostics/` | Tampering | Use `Path.iterdir()` and refuse to recurse into symlinks (`if entry.is_symlink(): continue`). Document in plan 04-03. |
| Diagnostics write leaks API keys if Phase 5 accidentally dumps full env into prompt.txt | Information Disclosure | Phase 5 concern, not Phase 4. Diagnostics API doesn't auto-dump anything; callers control what's written. Flag in authoring guide. |
| `subprocess.run(["pytest", ...])` for stage 5 — shell injection via mechanic_id | Elevation of Privilege | Never use `shell=True`; always pass argv as a list. Sanitize or validate mechanic-id / test-path before including in argv. |
| Temp file leakage on crash mid `_atomic_write_json` | Information Disclosure | Recovery: next `scan()` ignores `.tmp.*` files (predictable prefix); add a boot-time cleanup step to `DiagnosticsSink.__init__` that removes stale `*.tmp.*` files. |

**Positive controls already in codebase:**
- All SQL in `graph/persistence.py` and `graph/temporal.py` uses parameterized queries. [VERIFIED in 03-REVIEW.md]
- Mermaid emission escapes labels. [VERIFIED]
- `yaml.safe_load` everywhere. [VERIFIED]

**Phase 4 security deliverables:** AST rules (validation pipeline), symlink-safe prune-diagnostics, argv-list subprocess for pytest stage, boot-time temp-file cleanup in DiagnosticsSink.

## Sources

### Primary (HIGH confidence)
- `.planning/phases/04-llm-mechanic-generation/04-CONTEXT.md` — locked decisions D-01..D-38 (authoritative)
- `.planning/REQUIREMENTS.md` — MECH-03..06, TEST-02, AUTO-02, UNIV-03
- `.planning/GAP-HANDOFF.md` — 28 Phase-4 gap routing (MECH01–MECH27, GAP-ENG16)
- `.planning/GAP-ANALYSIS.md` — gap details for MECH gaps including framework-gap dependencies
- `.planning/phases/03-design-validation/03-REVIEW.md` — H-01 (temporal.py) and M-04 (use_cases/loader.py) fix scope
- Existing source files read directly: `src/token_world/mechanic/{loader,registry,protocol,context,engine,matchers}.py`, `src/token_world/mechanic/seeds/*/mechanic.py`, `src/token_world/use_cases/loader.py`, `src/token_world/graph/temporal.py`, `src/token_world/universe/scaffold.py`, `src/token_world/universe/templates/claude_md.py`, `src/token_world/mcp_server.py`, `src/token_world/cli.py`
- `pyproject.toml` — dependency + pytest config
- Python 3.12 stdlib docs (`ast`, `os.replace`, `importlib.util`, `tempfile`, `inspect`, `subprocess`, `contextlib`) — VERIFIED via direct imports + Python docs
- Sample use-case manifest `.planning/use-cases/spatial/UC-S01-movement-through-doorway.md` — manifest shape confirmed

### Secondary (MEDIUM confidence)
- pytest parametrize docs (docs.pytest.org) — pattern is stable since pytest 4.x, verified against pytest 7 installed locally
- `os.replace` atomicity on POSIX + Windows — documented in Python docs since 3.3

### Tertiary (LOW confidence — flagged as [ASSUMED])
- Bandit / pylint plugin API overhead assumption — not verified against current docs; if seeds grow past 15 AST rules, revisit at plan 04-02
- Ruff plugin API maturity as of 2026-04 — not verified this session; if ruff supports custom rules now, revisit
- mtime_ns resolution on Windows NTFS — assumed adequate; verify on first Windows operator session

## Metadata

**Confidence breakdown:**
- Standard stack (Python stdlib + existing deps): HIGH — every piece verified against codebase or stdlib docs
- Architecture patterns (AST visitor, validation pipeline, DiagnosticsSink, pytest parametrize, module discovery): HIGH — all are textbook Python patterns with clear stdlib support
- Pitfalls (H-01 deep fix, cache invalidation, framework-gap stub convention, CLRF regression, register_mechanic grep coverage): HIGH — identified from direct code inspection and review findings
- Wave parallelism for 27 seeds: MEDIUM — clustering proposal is sound but exact boundaries are Claude's Discretion (D-37); concrete dependency graph grows as cluster 1 ships
- Security coverage: MEDIUM — v1 explicitly deprioritizes runtime sandboxing; AST rules are the only new controls

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (30 days — Python stdlib is stable; revisit sooner only if ruff/bandit plugin APIs mature materially)

---

*Research conducted by gsd-researcher; consumed by gsd-planner for plan 04-01 through 04-NN.*
