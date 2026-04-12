---
phase: 00-universe-infrastructure
plan: 02
subsystem: infra
tags: [scaffold, mcp, claude-md, git-init, templates, json-rpc]

# Dependency graph
requires:
  - phase: 00-universe-infrastructure/01
    provides: "UniverseManager CRUD, XDG paths, Pydantic models, CLI, pyproject.toml"
provides:
  - "scaffold_universe() creates complete universe folder structure"
  - "CLAUDE.md template with World Rules, Available Tools, Current State, Constraints"
  - "AGENTS.md as relative symlink to CLAUDE.md"
  - ".mcp.json pointing to token-world-mcp via uvx"
  - "MCP stdio server stub with 4 tool declarations (resume_tick, rollback, list_mechanics, register_mechanic)"
  - "tick_summaries/{ticks,batches,epochs}/ directory hierarchy"
  - "Git-initialized universe folder with initial commit"
affects: [01-knowledge-graph, 02-mechanic-framework, 05-simulation-engine]

# Tech tracking
tech-stack:
  added: [ruff]
  patterns: [string.Template for text generation, JSON-RPC stdio protocol for MCP, subprocess git init for universe repos]

key-files:
  created:
    - src/token_world/universe/scaffold.py
    - src/token_world/universe/templates/__init__.py
    - src/token_world/universe/templates/claude_md.py
    - src/token_world/universe/templates/mcp_config.py
    - src/token_world/mcp_server.py
    - tests/test_universe/test_scaffold.py
    - tests/test_mcp_server.py
  modified:
    - src/token_world/universe/manager.py
    - pyproject.toml

key-decisions:
  - "Used string.Template (stdlib) for CLAUDE.md generation -- no external template dependency"
  - "MCP server uses raw JSON-RPC over stdio -- no external MCP library needed for Phase 0 stub"
  - "Used uvx --from token-world token-world-mcp in .mcp.json for portability"
  - "Git identity for universe commits set to Token World <token-world@localhost>"

patterns-established:
  - "Template pattern: render_* functions in src/token_world/universe/templates/ returning strings"
  - "Scaffold pattern: scaffold_universe() called by manager.create() after _init_db()"
  - "MCP handler pattern: handle_request() dispatches on JSON-RPC method string"

requirements-completed: [UNIV-01, UNIV-02, UNIV-03, UNIV-05, UNIV-06]

# Metrics
duration: 6min
completed: 2026-04-12
---

# Phase 0 Plan 02: Universe Scaffolding and MCP Stub Summary

**Universe scaffold with CLAUDE.md template, AGENTS.md symlink, .mcp.json, git init, and MCP stdio server stub declaring 4 tools**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-12T04:24:04Z
- **Completed:** 2026-04-12T04:30:26Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- scaffold_universe() creates all 9 required items in a universe folder (CLAUDE.md, AGENTS.md symlink, .mcp.json, universe.db, mechanics/, agents/, tick_summaries/, .git/, .gitignore)
- MCP server stub handles initialize, tools/list, tools/call with proper JSON-RPC protocol, declaring resume_tick, rollback, list_mechanics, and register_mechanic
- Full end-to-end integration: `token-world create` produces complete universe with all scaffold artifacts, `token-world list` shows it, `token-world delete` removes it
- 57 total tests pass (35 new + 22 existing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Universe scaffolding** - `19af2a3` (test) + `47817dd` (feat) -- TDD RED/GREEN
2. **Task 2: MCP server stub and .mcp.json** - `3be38e6` (test) + `afca73e` (feat) -- TDD RED/GREEN

_TDD tasks have two commits each: failing tests then implementation._

## Files Created/Modified
- `src/token_world/universe/scaffold.py` - scaffold_universe() creating dirs, CLAUDE.md, AGENTS.md, .mcp.json, .gitignore, git init
- `src/token_world/universe/templates/__init__.py` - Templates package init
- `src/token_world/universe/templates/claude_md.py` - render_claude_md() using string.Template
- `src/token_world/universe/templates/mcp_config.py` - render_mcp_json() generating .mcp.json
- `src/token_world/mcp_server.py` - MCP stdio server stub with JSON-RPC handler
- `src/token_world/universe/manager.py` - Added scaffold_universe() call in create(), fixed UP017 lint
- `pyproject.toml` - Added token-world-mcp script entry point, ruff dev dependency
- `tests/test_universe/test_scaffold.py` - 22 scaffold tests (dirs, CLAUDE.md, AGENTS.md, .mcp.json, git, integration)
- `tests/test_mcp_server.py` - 13 MCP server tests (initialize, tools/list, tools/call, errors)

## Decisions Made
- Used `string.Template` (stdlib) for CLAUDE.md generation per research recommendation -- no Jinja2 needed for simple substitution
- MCP server implemented as raw JSON-RPC over stdio -- no external MCP library keeps dependencies minimal for a Phase 0 stub
- .mcp.json uses `uvx --from token-world token-world-mcp` for portability across installations
- Git identity for universe commits uses "Token World" / "token-world@localhost" to distinguish universe commits from project commits

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added ruff to dev dependencies**
- **Found during:** Task 2 (ruff lint/format check)
- **Issue:** ruff was configured in pyproject.toml but not installed as a dev dependency, so `uv run ruff` failed
- **Fix:** Added ruff to dev dependency group via `uv add --dev ruff`
- **Files modified:** pyproject.toml
- **Verification:** `uv run ruff check src/` and `uv run ruff format --check src/` both pass
- **Committed in:** afca73e (Task 2 commit)

**2. [Rule 1 - Bug] Fixed UP017 lint violation in manager.py**
- **Found during:** Task 2 (ruff lint check)
- **Issue:** `timezone.utc` should be `UTC` (imported from datetime) per Python 3.11+ style
- **Fix:** Changed `from datetime import datetime, timezone` to `from datetime import UTC, datetime` and `timezone.utc` to `UTC`
- **Files modified:** src/token_world/universe/manager.py
- **Verification:** ruff check passes clean
- **Committed in:** afca73e (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for build tooling and lint compliance. No scope creep.

**Out-of-scope lint issues noted:** B904 in cli.py (2 instances), UP017 in models.py (1 instance) -- pre-existing, not in files created by this plan.

## Issues Encountered
None - all implementation followed the plan specification.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Universe folder scaffolding complete with all required artifacts
- MCP tool stubs are discoverable; real implementations will be added in Phases 1-5
- CLAUDE.md template ready for extension as new capabilities are added
- Existing tests (57 total) provide regression safety for Phase 1 (knowledge graph)

## Self-Check: PASSED

All 8 created files verified on disk. All 4 task commits verified in git log.

---
*Phase: 00-universe-infrastructure*
*Completed: 2026-04-12*
