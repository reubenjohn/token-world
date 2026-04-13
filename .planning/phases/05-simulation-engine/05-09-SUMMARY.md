---
phase: 05-simulation-engine
plan: "09"
subsystem: mcp-server
tags:
  - mcp
  - simulation
  - resume_tick
  - rollback
  - list_mechanics
  - UNIV-03
  - gap-closure

# Dependency graph
requires:
  - phase: 05-simulation-engine
    provides: >
      SimulationEngine.run_tick (05-08), KnowledgeGraph.restore (Phase 1),
      MechanicRegistry.list_mechanics (Phase 2/4), YieldSignal.to_json (Phase 4.1)

provides:
  - "resume_tick MCP tool: calls SimulationEngine.run_tick(action_text, actor) -> JSON payload"
  - "rollback MCP tool: calls KnowledgeGraph.restore(snapshot_id) -> confirmed tick_id"
  - "list_mechanics MCP tool: calls MechanicRegistry.list_mechanics() -> sorted list with optional filter"
  - "Path-traversal defence on universe_path (..' rejected)"
  - "-32602 Invalid params on missing/invalid params; -32603 Internal error on exceptions"
  - "No stack-trace leak to JSON-RPC stdout (full trace to stderr only)"

affects:
  - "05-10 (MCP tool wiring — same file, superseded)"
  - "05-12 (verification — MCP surface now testable end-to-end)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_anthropic_factory module-level monkeypatch surface for test injection"
    - "Lazy imports of SimulationEngine/KnowledgeGraph inside tool functions to keep module import cheap"
    - "_InvalidParams exception class for clean -32602 error routing"
    - "try/except _InvalidParams then broad except for -32603 in tools/call dispatcher"

key-files:
  created:
    - tests/test_universe/test_mcp_tools.py
  modified:
    - src/token_world/mcp_server.py
    - tests/test_mcp_server.py

key-decisions:
  - "Lazy imports inside each _tool_* function — module import stays cheap for tests that only test the dispatcher"
  - "_anthropic_factory module-level variable (not constructor injection) — MCP server is a module not a class; monkeypatch is the idiomatic test pattern"
  - "rollback returns -32602 (not -32603) when universe.db is missing — this is a param validation failure (caller passed a path without a db), not an internal error"
  - "tests/test_mcp_server.py Phase 0 stub tests updated — two tests that asserted 'not yet implemented' text were replaced with real error-code assertions (Rule 1 auto-fix)"

requirements-completed:
  - UNIV-03

# Metrics
duration: 5min
completed: 2026-04-13
---

# Phase 5 Plan 09: MCP Tool Wiring Summary

**Real SimulationEngine/KnowledgeGraph/MechanicRegistry implementations replace Phase 0 stubs in all three MCP tools with path-traversal defence, -32602/-32603 error routing, and no stack-trace leaks**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-13T14:15:11Z
- **Completed:** 2026-04-13T14:19:41Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- `resume_tick` MCP tool: constructs fresh `SimulationEngine` + `KnowledgeGraph` from `universe_path`, calls `run_tick(action_text, actor)`, serialises `TickResult` to JSON payload
- `rollback` MCP tool: loads `KnowledgeGraph` from `universe_path/universe.db`, calls `restore(snapshot_id)`, returns `{ok, snapshot_id, restored_to_tick, rolled_back_from_tick}`
- `list_mechanics` MCP tool: constructs `MechanicRegistry(universe_path/mechanics)`, returns `{count, mechanics: [{id, description, voluntary, tags}]}` with optional substring filter
- `_require_universe_path`: path-traversal defence — rejects `'..'` segments before resolving; verifies directory exists
- `_anthropic_factory` monkeypatch surface so tests never call the real Anthropic API
- TOOLS inputSchema tightened: all three tools now declare `universe_path` as required
- Module docstring updated to describe real implementations (no longer says "returns 'not implemented' for each")
- 29 new tests in `tests/test_universe/test_mcp_tools.py` covering execute/yield paths, rollback restore, filter, all error codes, path-traversal, anti-pattern (stub string absent)
- Full suite: 1216 passed (up from 1187 baseline)

## Task Commits

1. **Task 1: Real MCP tool implementations** — `d8bee27` (feat)

## Files Created/Modified

- `src/token_world/mcp_server.py` — Phase 0 stubs replaced; TOOLS inputSchema tightened; module docstring updated; `_tool_resume_tick`, `_tool_list_mechanics`, `_tool_rollback`, `_require_universe_path`, `_InvalidParams`, `_jsonrpc_error`, `_anthropic_factory`, `_build_anthropic_client` added
- `tests/test_universe/test_mcp_tools.py` — 29 new tests (CREATED)
- `tests/test_mcp_server.py` — two Phase 0 stub assertions updated to real error-code assertions

## Decisions Made

- **Lazy imports** inside each `_tool_*` function: `SimulationEngine`, `KnowledgeGraph`, `MechanicRegistry` are imported only when the tool runs, not at module load. Keeps the MCP server's import-time cost minimal.
- **`_anthropic_factory` module-level variable**: MCP server is a module, not a class. Monkeypatching a module-level callable is the idiomatic pattern (matches `classifier.py`). Constructor injection is not possible without turning the server into a class.
- **`rollback` missing `universe.db` → -32602 not -32603**: A missing database is a caller-side error (the universe_path they passed doesn't have a db yet), not an internal server error.
- **`graph.save()` after rollback**: Ensures the SQLite file reflects the restored state so subsequent `resume_tick` calls start from the right tick. Documented in plan risks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two Phase 0 stub tests in test_mcp_server.py asserted old stub behavior**
- **Found during:** Task 1 (first GREEN run of full suite)
- **Issue:** `test_tools_call_returns_not_implemented` and `test_tools_call_includes_tool_name_in_response` in `tests/test_mcp_server.py` asserted `"not yet implemented"` text that no longer exists after the stubs were replaced. Both tests crashed with `KeyError: 'result'`.
- **Fix:** Updated both tests to assert real error-code behavior (`-32602` returned for missing `universe_path`). Behavior is now correct and verifiable.
- **Files modified:** `tests/test_mcp_server.py`
- **Commit:** d8bee27

## Known Stubs

None — all three MCP tool stubs are fully replaced.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes beyond what the plan's threat model already covers (`T-05-MCP-PATH-TRAVERSAL` mitigated by `_require_universe_path`).

## Self-Check: PASSED

- `src/token_world/mcp_server.py` — FOUND
- `tests/test_universe/test_mcp_tools.py` — FOUND
- Commit `d8bee27` — FOUND
- `"This is a Phase 0 stub."` not in mcp_server.py — CONFIRMED
- `uv run pytest -x -q` — 1216 passed
- `git diff bc3e0cf..HEAD --stat` — only 3 files (mcp_server.py, test_mcp_server.py, test_mcp_tools.py)
