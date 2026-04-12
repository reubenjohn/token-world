---
phase: 02-mechanic-framework
plan: 03
subsystem: mechanic-registry-cli
tags: [registry, cli, loader, git-versioning, mechanic-discovery]
dependency_graph:
  requires: [02-01, 02-02]
  provides: [MechanicRegistry, MechanicInfo, MechanicVersion, load_mechanic_class, list-mechanics-cli, run-mechanic-cli, query-graph-cli]
  affects: [src/token_world/mechanic/, src/token_world/cli.py]
tech_stack:
  added: [types-PyYAML]
  patterns: [importlib-dynamic-loading, subprocess-git-log, click-cli-commands, yaml-safe-load]
key_files:
  created:
    - src/token_world/mechanic/loader.py
    - src/token_world/mechanic/registry.py
    - tests/test_mechanic/test_registry.py
    - tests/test_mechanic/test_cli.py
  modified:
    - src/token_world/mechanic/__init__.py
    - src/token_world/cli.py
    - pyproject.toml
decisions:
  - Used importlib.util.spec_from_file_location for dynamic loading to avoid module name collisions
  - Registry auto-scans on init; meta.yaml provides tags and metadata, falls back to class attributes
  - Git history uses list-form subprocess.run (never shell=True) per threat model T-02-09
  - CLI commands use lazy imports to avoid circular dependency issues
metrics:
  duration: 291s
  completed: "2026-04-12T08:12:45Z"
  tasks: 2/2
  files: 7
  tests_added: 20
  total_tests: 216
---

# Phase 02 Plan 03: Mechanic Registry and CLI Summary

Dynamic mechanic loader using importlib, folder-scanning registry with yaml.safe_load metadata and git-log version history, plus three CLI commands (list-mechanics, run-mechanic, query-graph) for mechanic discovery and execution.

## Task Results

### Task 1: Mechanic loader and registry with git versioning

| Aspect | Detail |
|--------|--------|
| Status | Complete |
| TDD | RED a830063, GREEN f854c32 |
| Tests | 11 passing |

**loader.py**: `load_mechanic_class()` dynamically imports mechanic.py from a folder, validates Mechanic subclass existence. Uses `importlib.util.spec_from_file_location` with unique module names to avoid caching conflicts.

**registry.py**: `MechanicRegistry` scans a mechanics/ directory, loads meta.yaml via `yaml.safe_load()`, indexes by id, supports `list_mechanics()`, `get_mechanic()`, `get_info()`, `query_by_tag()`, and `get_history()`. Git history retrieval uses list-form `subprocess.run(["git", "log", ...])` and returns empty list gracefully if not in a git repo.

### Task 2: CLI commands (list-mechanics, run-mechanic, query-graph)

| Aspect | Detail |
|--------|--------|
| Status | Complete |
| TDD | RED cbf0251, GREEN 4645746 |
| Tests | 9 passing |

**list-mechanics**: Shows all mechanics with id, voluntary/involuntary flag, and description.

**run-mechanic**: Loads graph from universe.db, instantiates mechanic via registry, executes with ChainExecutionEngine (including involuntary chain reactions), displays check result, mutations, trace summary, and saves graph.

**query-graph**: Inspects graph with `--type` (agent/entity), `--has-property`, `--near`, `--limit`, `--stats`, `--json` options. Supports both human-readable and JSON output formats.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed monkeypatch target for CLI tests**
- **Found during:** Task 2 GREEN phase
- **Issue:** Tests patched `token_world.universe.paths.get_universes_dir` but UniverseManager uses `from` import, so the already-bound name in the manager module was not affected.
- **Fix:** Changed monkeypatch target to `token_world.universe.manager.get_universes_dir`
- **Files modified:** tests/test_mechanic/test_cli.py

**2. [Rule 1 - Bug] Fixed query-graph type-agent test assertion**
- **Found during:** Task 2 GREEN phase
- **Issue:** Test asserted `"room_a" not in result.output` but "room_a" appeared as alice's location property value, not as a node entry.
- **Fix:** Changed assertion to check `"room_a:" not in result.output` (node ID prefix format)
- **Files modified:** tests/test_mechanic/test_cli.py

**3. [Rule 3 - Blocking] Added types-PyYAML dev dependency**
- **Found during:** Task 2 verification
- **Issue:** mypy failed with "Library stubs not installed for yaml"
- **Fix:** Added `types-PyYAML` as dev dependency via `uv add --dev types-PyYAML`
- **Files modified:** pyproject.toml

## Threat Model Compliance

- T-02-09: Git subprocess uses list-form `subprocess.run(["git", "log", ...])` -- never `shell=True`
- T-02-10: YAML deserialization uses `yaml.safe_load()` exclusively
- T-02-12: Universe slug validated by `UniverseManager.load()` existing path traversal prevention

## Known Stubs

None -- all functionality is fully wired.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| a830063 | test | Add failing tests for mechanic loader and registry (11 tests) |
| f854c32 | feat | Implement mechanic loader and registry with git versioning |
| cbf0251 | test | Add failing tests for CLI commands (9 tests) |
| 4645746 | feat | Implement CLI commands list-mechanics, run-mechanic, query-graph |

## Self-Check: PASSED

All 4 created files exist. All 4 commit hashes verified in git log.
