---
phase: 04-llm-mechanic-generation
plan: 01
subsystem: mechanic-framework
tags: [refactor, flat-layout, registry, mcp, test-migration, phase3-fixes]
requires:
  - Phase 2 mechanic framework (protocol.py, registry.py, loader.py, engine.py, matchers.py)
  - Phase 3 temporal.py + use_cases/loader.py (H-01/M-04 fixes already merged from code-review-fix worktree into master)
provides:
  - Flat-module mechanic layout (seeds/<id>.py, no meta.yaml)
  - discover_mechanic_modules + load_mechanic_classes loader API
  - Mechanic.tags: list[str] = [] default (D-04)
  - MechanicRegistry with duplicate-id rejection (T-04)
  - 3-tool MCP surface (resume_tick, rollback, list_mechanics)
  - Scaffold of flat .py seeds + universe/tests/test_mechanics/ mirrored tree
  - Universe CLAUDE.md template with Mechanic Authoring section (no register_mechanic)
  - H-01/M-04 regression tests (named per plan Task 4)
  - VALIDATION.md Per-Task Verification Map rows 04-01-T1..T5
affects:
  - src/token_world/mechanic/{protocol,loader,registry,__init__,seeds/*}.py
  - src/token_world/universe/{scaffold,templates/claude_md}.py
  - src/token_world/mcp_server.py
  - tests/test_mechanic/* (migration to test_seeds/ + new test_loader.py + rewrite test_registry.py)
  - tests/test_mcp_server.py (3-tool assertions)
  - tests/test_universe/test_scaffold.py (flat layout + Mechanic Authoring assertions)
  - tests/test_graph/test_temporal_index.py (new named regression test)
  - tests/test_design_validation/test_use_case_schema.py (new CRLF + CR regression tests)
  - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md
tech-stack:
  added: []
  patterns:
    - "Module-based discovery: importlib.util.spec_from_file_location with attr.__module__ == module_name filter to prevent re-detection of imported Mechanic base"
    - "Mirrored test tree: tests/test_mechanic/test_seeds/test_<id>.py mirrors src/token_world/mechanic/seeds/<id>.py — git mv preserves history"
    - "Registry duplicate-id guard: raises ValueError with prior path in the message (T-04-REGISTRY-SHADOWING mitigation)"
    - "Scaffold copy flat .py files but skip __init__.py; underscore prefix is the registry's skip signal, not the scaffold's"
key-files:
  created:
    - src/token_world/mechanic/seeds/_helpers.py
    - tests/test_mechanic/test_loader.py
    - tests/test_mechanic/test_seeds/__init__.py
  modified:
    - src/token_world/mechanic/protocol.py (Mechanic.tags default added)
    - src/token_world/mechanic/loader.py (rewritten for module-based discovery)
    - src/token_world/mechanic/registry.py (rewritten; removed yaml + meta.yaml branch; duplicate-id guard)
    - src/token_world/mechanic/__init__.py (export rename: load_mechanic_class -> discover_mechanic_modules + load_mechanic_classes)
    - src/token_world/universe/scaffold.py (flat copy + mirrored test tree + slug param to render_claude_md)
    - src/token_world/universe/templates/claude_md.py (Mechanic Authoring section; slug substitution)
    - src/token_world/mcp_server.py (3-tool TOOLS list)
    - tests/test_mechanic/test_registry.py (rewritten for flat layout)
    - tests/test_mcp_server.py (3-tool assertions + negative register_mechanic)
    - tests/test_universe/test_scaffold.py (flat-layout + mirrored test tree + Mechanic Authoring assertions)
    - tests/test_graph/test_temporal_index.py (added test_find_state_at_tick_handles_remove_then_readd)
    - tests/test_design_validation/test_use_case_schema.py (added CRLF + CR regression tests)
    - .planning/phases/04-llm-mechanic-generation/04-VALIDATION.md (per-task rows)
  renamed:
    - src/token_world/mechanic/seeds/movement/mechanic.py -> src/token_world/mechanic/seeds/movement.py (git mv, 98% similarity)
    - src/token_world/mechanic/seeds/observation/mechanic.py -> src/token_world/mechanic/seeds/observation.py (git mv, 97% similarity)
    - src/token_world/mechanic/seeds/environmental_reaction/mechanic.py -> src/token_world/mechanic/seeds/environmental_reaction.py (git mv, 99% similarity)
    - tests/test_mechanic/test_seed_movement.py -> tests/test_mechanic/test_seeds/test_movement.py (git mv, 98% similarity)
    - tests/test_mechanic/test_seed_observation.py -> tests/test_mechanic/test_seeds/test_observation.py (git mv, 96% similarity)
    - tests/test_mechanic/test_seed_environmental.py -> tests/test_mechanic/test_seeds/test_environmental.py (git mv, 99% similarity)
  deleted:
    - src/token_world/mechanic/seeds/movement/__init__.py
    - src/token_world/mechanic/seeds/movement/meta.yaml
    - src/token_world/mechanic/seeds/movement/tests/.gitkeep
    - src/token_world/mechanic/seeds/observation/__init__.py
    - src/token_world/mechanic/seeds/observation/meta.yaml
    - src/token_world/mechanic/seeds/observation/tests/.gitkeep
    - src/token_world/mechanic/seeds/environmental_reaction/__init__.py
    - src/token_world/mechanic/seeds/environmental_reaction/meta.yaml
    - src/token_world/mechanic/seeds/environmental_reaction/tests/.gitkeep
decisions:
  - Applied D-04 (Mechanic.tags as class attribute) as the single source of truth for classification; meta.yaml removed everywhere.
  - Applied D-10 (flat module layout + 3-tool MCP + operator-side SDLC authoring).
  - H-01 and M-04 source fixes were ALREADY MERGED from the code-review-fix worktree (see plan's important note). This plan added the named regression tests; the src/ behaviour already matched.
metrics:
  duration: ~20 min
  completed: 2026-04-12
---

# Phase 4 Plan 01: Flatten mechanic layout + drop register_mechanic + Phase 3 H-01/M-04 fixes — Summary

Flat-layout cornerstone for Phase 4: seed mechanics are now `<id>.py` modules with class-level `id/description/voluntary/tags`, the registry discovers modules (not folders), `register_mechanic` is removed from the MCP surface, tests live in the mirrored tree, and H-01/M-04 have named regression tests.

## What Changed

### Flat seed layout (Task 1)
- Moved `mechanic/seeds/{movement,observation,environmental_reaction}/mechanic.py` to `mechanic/seeds/<id>.py` via `git mv` (98/97/99% similarity preserved).
- Removed all `meta.yaml`, per-seed `__init__.py`, and empty `tests/` subfolders.
- Added `tags: list[str] = []` class-level default on `Mechanic` ABC (D-04). Each seed declares its own tags: `MovementMechanic.tags = ["spatial", "core"]`, `ObservationMechanic.tags = ["perception", "core"]`, `EnvironmentalReactionMechanic.tags = ["environmental", "reactive", "core"]` (mirror previous `meta.yaml` values).
- New `seeds/_helpers.py` stub — registry-invisible per D-05, grows organically.

### Module-based loader (Task 1)
- `loader.py` rewritten. New public API:
  - `discover_mechanic_modules(mechanics_dir) -> list[Path]` — sorted `.py` files, skipping `__init__.py` and any `_*.py`. Returns `[]` for non-existent directories.
  - `load_mechanic_classes(module_path) -> list[type[Mechanic]]` — returns every concrete `Mechanic` subclass defined *in that module* (filters by `attr.__module__ == module_name` so imported bases aren't re-detected). Empty module → `[]` (not an error). Missing file → `FileNotFoundError`.
- Old `load_mechanic_class` (singular) removed everywhere in `src/` and `tests/`.

### Registry (Task 2)
- `MechanicRegistry.scan()` rewritten: walks `discover_mechanic_modules`, registers every subclass returned by `load_mechanic_classes`. Reads metadata from class attributes only.
- T-04-REGISTRY-SHADOWING mitigation: raises `ValueError("Duplicate mechanic id {id!r} in {path} (already registered from {prior_path})")` when two modules declare the same `id`.
- Removed `import yaml` and `meta.yaml` handling entirely.
- `get_history` body unchanged — `git log -- <path>` works equally for files and folders.

### Test migration (Task 2)
- `git mv tests/test_mechanic/test_seed_<name>.py tests/test_mechanic/test_seeds/test_<name>.py` — history preserved.
- Rewrote imports to flat module paths (e.g., `from token_world.mechanic.seeds.movement import MovementMechanic`).
- Rewrote `test_registry.py` with the flat-layout contract tests (discovery, underscore skip, `__init__` skip, duplicate id, meta.yaml ignored, query_by_tag, seed integration, git history).
- New `test_loader.py` with loader-contract tests (empty module returns `[]`, missing file raises, import filter works, multi-mechanic modules per D-03, sort order).

### Scaffold + MCP + CLAUDE.md template (Task 3)
- `scaffold.py::_copy_seed_mechanics` rewritten: copies flat `.py` files (and `_helpers.py`), excluding `__init__.py` (destination is not a Python package).
- `scaffold_universe` now creates `tests/test_mechanics/__init__.py` as the mirrored test tree root (D-06).
- `render_claude_md(*, name, slug)` — `slug` added to enable the authoring-tool example placeholder.
- CLAUDE.md template: `### register_mechanic` section replaced by `## Mechanic Authoring` (points at flat layout + `docs/authoring-mechanics.md` that Phase 4 plan 04-05 writes).
- `mcp_server.py::TOOLS` shrunk from 4 to 3 entries (register_mechanic dropped). Docstring updated.

### H-01 and M-04 regression tests (Task 4)
- IMPORTANT: source-level H-01 (TemporalIndex add_node payload seeding) and M-04 (use_cases loader CRLF normalisation) fixes were ALREADY merged from the `code-review-fix` worktree into master before this plan ran. The executor confirmed the plan's source edits were already in place and did not re-apply them.
- Added the plan-named regression tests:
  - `tests/test_graph/test_temporal_index.py::test_find_state_at_tick_handles_remove_then_readd` — covers Pitfall 7 (add_node seeds state + subsequent set_property refines it).
  - `tests/test_design_validation/test_use_case_schema.py::test_load_use_case_accepts_crlf_frontmatter` + bonus `test_load_use_case_accepts_legacy_mac_cr_frontmatter`.
- Complements pre-existing H-01 regression tests (`test_find_state_at_tick_remove_then_readd_clears_stale_props`, `test_find_state_at_tick_readd_with_initial_props_seeds_state`).

### VALIDATION.md (Task 5)
- Replaced the placeholder `—` row with rows 04-01-T1..T5, one per task; status ✅ passing.

## Test Counts

- **Before:** 291 passed.
- **After:** 311 passed (+20 = 5 new registry scan tests + 9 new loader tests + 3 scaffold tests + 1 MCP negative test + 1 temporal regression + 2 use-case CRLF/CR regressions — net of test migrations that preserved existing test count).
- **Lint:** `ruff check src/` clean.
- **Format:** `ruff format --check src/` clean (37 files).
- **mypy:** `mypy src/token_world/mechanic/ src/token_world/graph/temporal.py src/token_world/use_cases/loader.py` clean.

## Gotchas Surfaced

1. **H-01/M-04 already fixed.** The plan's Task 4 Steps A and B would have re-applied `elif e.event_type == "add_node": state = json.loads(...)` and the `replace("\r\n", "\n")` normalisation. Both already existed in `src/` (from the code-review-fix merge). Executor skipped the source edits and only added the named regression tests, per the important-note in the prompt.
2. **Stale `__pycache__` after `git mv`.** Directory listings still showed `movement/ observation/ environmental_reaction/` after `git mv` + `git rm -r` because Python had written `__pycache__/*.pyc` there. Fixed with `rm -rf` on the orphan dirs and `find ... -name __pycache__ -exec rm -rf`.
3. **`render_claude_md` signature change is load-bearing.** Adding `slug` as a required keyword-only param broke the one call site in `scaffold.py`; fixed inline. No downstream callers exist yet outside the project.
4. **Scaffold copies `_helpers.py` but not `__init__.py`.** This is deliberate: `_` is the *registry's* skip signal, but the scaffold needs helpers in the universe for seeds that reference them. `__init__.py` is excluded because the destination (`mechanics/`) is not a Python package — mechanics are loaded via `importlib.util.spec_from_file_location`, not `import`.
5. **Mechanic ABC `tags: list[str] = []` is a class-level default, not an `__init__` mutable default.** Subclasses always override with their own `tags = [...]` class attributes, so no shared-mutation foot-gun. (The `list[str] = []` annotation pattern is identical to how `voluntary: bool = True` already worked.)

## Notes for Downstream Plans

- **`_helpers.py` is empty.** No shared seed patterns have emerged yet. Plans 04-02 through 04-05 should resist over-extracting — grow `_helpers.py` only when two seeds repeat identical logic.
- **No Mechanic protocol additions beyond `tags`.** The ABC still exposes `id`, `description`, `voluntary`, `tags`, `check`, `apply`, `watches`. Downstream plans (validation, mechanic generation) can key off `tags` for categorical filtering without schema churn.
- **Registry duplicate-id error message names both paths.** `f"Duplicate mechanic id {id!r} in {new_path} (already registered from {prior_path})"`. Validation plans (04-02) and the diagnostics sink (04-04) can parse or match this format for structured reporting.
- **Mirrored test tree exists but is empty in scaffolded universes.** `universe/tests/test_mechanics/__init__.py` is written. Plan 04-03 (integration harness) and 04-05 (authoring guide) can assume it's present.
- **MCP tool surface is now exactly 3.** `resume_tick`, `rollback`, `list_mechanics`. Any plan that needs a new MCP tool should open a decision checkpoint — the operator-side SDLC philosophy (D-10) deliberately keeps the surface small.

## Commits

| Task | Commit | Type | Summary |
|------|--------|------|---------|
| T1   | f579631 | refactor | flatten seed modules + module-based loader + Mechanic.tags |
| T2   | 6f0ae72 | refactor | rewrite registry for flat discovery + migrate seed tests |
| T3   | bbc6a87 | refactor | drop register_mechanic + scaffold flat seeds + mirrored tests |
| T4   | b4bf4ae | test     | add H-01/M-04 regression tests (fixes already in master) |
| T5   | 0692dfa | docs     | record per-task verification map (04-01-T1..T5) |

## Self-Check: PASSED

- All 5 per-task commits present in `git log --oneline` (f579631, 6f0ae72, bbc6a87, b4bf4ae, 0692dfa).
- All created files exist:
  - `src/token_world/mechanic/seeds/_helpers.py` ✓
  - `src/token_world/mechanic/seeds/{movement,observation,environmental_reaction}.py` ✓
  - `tests/test_mechanic/test_loader.py` ✓
  - `tests/test_mechanic/test_seeds/__init__.py` ✓
  - `tests/test_mechanic/test_seeds/test_{movement,observation,environmental}.py` ✓
- Deleted artefacts absent: no `movement/`, `observation/`, `environmental_reaction/` subdirectories under `src/token_world/mechanic/seeds/`; no `meta.yaml` under `src/token_world/mechanic/seeds/`.
- Full suite 311 passed, ruff + mypy clean.
- `load_mechanic_class` (singular) returns 0 matches in `src/` and `tests/`.
- `register_mechanic` in `src/mcp_server.py` is one docstring reference ("so there is no ``register_mechanic`` MCP tool"); in tests only in negative assertions — acceptable.
