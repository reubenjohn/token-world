---
phase: 06-resident-agent-end-to-end-loop
plan: 01
subsystem: resident-agent
tags: [anthropic-sdk, sqlite, pydantic, click, session-forking, agent-memory]

# Dependency graph
requires:
  - phase: 05-simulation-engine
    provides: SimulationEngine.run_tick, TickResult, YieldSignal
  - phase: 04.1-operator-agent-harness
    provides: OperatorHarness.handle_yield (async)
  - phase: 01-graph-foundation
    provides: KnowledgeGraph.snapshot/restore for session forking

provides:
  - PersonalityBundle (Pydantic model) + PersonalityGenerator (one-shot Sonnet)
  - AgentMemory (SQLite agent_memory + agent_sessions tables, rolling window + Haiku summary)
  - SessionManager (create/fork/restore sessions via graph snapshot)
  - ResidentAgent (raw Anthropic SDK loop, hash-stable system prompt, alternating context)
  - create_agent_node() helper (dict personality on graph node)
  - token-world agent-turn CLI command (auto-create agent, run one turn, print observation)

affects:
  - 06-04 (playtest runner reuses ResidentAgent + AgentMemory + SessionManager)
  - 06-05 (prompt-hash registry uses ResidentAgent.system_prompt_text())
  - 06-02 (tick compressor hooks into engine; no resident dep but same wave)

# Tech tracking
tech-stack:
  added: [pydantic v2 (PersonalityBundle), anthropic (raw SDK for resident agent)]
  patterns:
    - Raw Anthropic SDK loop (not Agent SDK) for resident agent text generation
    - SQLite lazy-table-init pattern (CREATE TABLE IF NOT EXISTS on first use)
    - Shared DDL helper (ensure_memory_tables) imported by both AgentMemory and SessionManager
    - Session forking via KnowledgeGraph.snapshot/restore (no DB copy, no git branch)
    - Hash-stable system prompt (world rules + personality; NO history in system prompt)
    - Alternating user/assistant messages from rolling window (last 10 turns)
    - Memory summary compression via Haiku at every 10-turn boundary

key-files:
  created:
    - src/token_world/resident/__init__.py
    - src/token_world/resident/personality.py
    - src/token_world/resident/memory.py
    - src/token_world/resident/session.py
    - src/token_world/resident/agent.py
    - tests/test_resident/__init__.py
    - tests/test_resident/conftest.py
    - tests/test_resident/test_personality.py
    - tests/test_resident/test_memory.py
    - tests/test_resident/test_session.py
    - tests/test_resident/test_agent.py
    - tests/test_resident/test_cli_agent_turn.py
  modified:
    - src/token_world/cli.py (added agent-turn command + module-level imports)

key-decisions:
  - "D-01/D-02: Resident agent uses raw Anthropic SDK (not Agent SDK); default model claude-haiku-4-5"
  - "D-03/D-26: PersonalityBundle is Pydantic model stored as dict on graph node + JSON in agent_sessions"
  - "D-04: System prompt = world_rules + personality block + static instruction; NO history in system prompt"
  - "D-05/D-06: Two SQLite tables (agent_memory, agent_sessions) with lazy-init DDL and parameterized queries"
  - "D-07/D-27: Rolling window=10 turns + Haiku memory summary regenerated every 10 turns"
  - "D-08: Session forking via KnowledgeGraph.snapshot/restore — no DB copy or git branch"
  - "D-21: ResidentAgent.run_turn() does NOT call SimulationEngine; caller orchestrates (clean separation)"
  - "D-22/D-29: agent-turn CLI auto-creates agent+session if none exist; asyncio.run bridges async handle_yield"

patterns-established:
  - "ensure_memory_tables(conn): shared DDL helper imported by both AgentMemory and SessionManager"
  - "Mock pattern: MockAnthropicClient with pre-programmed responses list, reused across all resident tests"
  - "TDD pattern: test file exists before implementation; all 5 task test modules written RED-first"
  - "CLI patch pattern: patch at token_world.cli.X for module-level imports (not deferred imports)"

requirements-completed: [AGENT-01, AGENT-02, AGENT-03, AGENT-04]

# Metrics
duration: ~75min
completed: 2026-04-13
---

# Phase 06 Plan 01: ResidentAgent Module Summary

**Personality-driven LLM resident agent with SQLite memory, graph-snapshot session forking, and interactive agent-turn CLI — closing the resident-agent half of the Phase 6 loop**

## Performance

- **Duration:** ~75 min
- **Started:** 2026-04-13T15:00:00Z (tasks 1-2 by prior executor; tasks 3-5 by this executor)
- **Completed:** 2026-04-13T16:07:43Z
- **Tasks:** 5
- **Files modified:** 13

## Accomplishments

- Full `src/token_world/resident/` package: PersonalityBundle/Generator, AgentMemory, SessionManager, ResidentAgent, create_agent_node
- `token-world agent-turn <slug>` CLI command with auto-create, yield handling via OperatorHarness, memory persistence
- 29 tests across 5 modules (all TDD, all green); full suite 1252 passing

## Task Commits

1. **Task 1: PersonalityBundle + PersonalityGenerator** - `f65419e` (feat)
2. **Task 2: AgentMemory (agent_memory + agent_sessions)** - `2d833a5` (feat)
3. **Task 3: SessionManager fork + restore via graph snapshot** - `94db614` (feat)
4. **Task 4: ResidentAgent raw Anthropic loop** - `5150ffa` (feat)
5. **Task 5: token-world agent-turn CLI command** - `9366f21` (feat)

## Files Created/Modified

- `src/token_world/resident/__init__.py` - Public API exports (PersonalityBundle, PersonalityGenerator, AgentMemory, SessionManager, ResidentAgent, create_agent_node)
- `src/token_world/resident/personality.py` - Pydantic PersonalityBundle with 3-5 trait validator; PersonalityGenerator one-shot Sonnet call with JSON extraction + retry
- `src/token_world/resident/memory.py` - AgentMemory SQLite adapter; lazy DDL; store_turn, get_context (rolling window), maybe_compact_summary (Haiku at 10-turn boundary); shared ensure_memory_tables() DDL helper
- `src/token_world/resident/session.py` - SessionManager with create/fork/restore/get/list/get_next_turn_number; fork via graph.snapshot; list_agents() for CLI auto-create
- `src/token_world/resident/agent.py` - ResidentAgent with _build_system_prompt (hash-stable, no history), _build_messages (alternating user/assistant), run_turn(); create_agent_node() module helper
- `src/token_world/cli.py` - Added agent-turn command; moved SimulationEngine and KnowledgeGraph to module-level imports for testability
- `tests/test_resident/` - 5 test modules (29 tests total) + conftest with MockAnthropicClient

## Decisions Made

- Used `ensure_memory_tables(conn)` as a shared module-level DDL function in memory.py, imported by SessionManager to avoid DDL duplication (not in plan; obvious quality improvement)
- Moved `SimulationEngine` and `KnowledgeGraph` to module-level imports in cli.py (plan had them as deferred); required for test monkeypatching at `token_world.cli.X`
- `get_next_turn_number` added to SessionManager (plan mentioned it; implemented alongside fork/restore)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff UP037 quoted annotations in session.py**
- **Found during:** Task 3 (SessionManager)
- **Issue:** `graph: "KnowledgeGraph"` annotations with string quotes triggered ruff UP037 (redundant with `from __future__ import annotations` already present)
- **Fix:** `uv run ruff check --fix` removed quotes
- **Files modified:** `src/token_world/resident/session.py`
- **Verification:** ruff passes
- **Committed in:** `94db614`

**2. [Rule 1 - Bug] mypy no-any-return in session.py get_next_turn_number**
- **Found during:** Task 3 (SessionManager)
- **Issue:** `return row[0] + 1` returned `Any` (sqlite3 row element type); mypy flagged `no-any-return`
- **Fix:** Cast to `int(row[0]) + 1`
- **Files modified:** `src/token_world/resident/session.py`
- **Verification:** `uv run mypy src/token_world/resident/` clean
- **Committed in:** `94db614`

**3. [Rule 1 - Bug] mypy no-any-return in agent.py run_turn**
- **Found during:** Task 4 (ResidentAgent)
- **Issue:** `response.content[0].text.strip()` returned `Any` (Anthropic SDK typing)
- **Fix:** `str(response.content[0].text).strip()` to explicitly cast
- **Files modified:** `src/token_world/resident/agent.py`
- **Verification:** `uv run mypy src/token_world/resident/` clean
- **Committed in:** `5150ffa`

**4. [Rule 2 - Missing] Deferred imports in agent-turn broke monkeypatching**
- **Found during:** Task 5 (CLI), test_agent_turn_auto_creates_agent_when_none_exists
- **Issue:** Plan had SimulationEngine and KnowledgeGraph as deferred imports inside agent_turn function body; `patch("token_world.cli.KnowledgeGraph")` raised AttributeError
- **Fix:** Moved both to module-level imports; removed deferred import block from function body
- **Files modified:** `src/token_world/cli.py`
- **Verification:** All 5 CLI tests pass
- **Committed in:** `9366f21`

---

**Total deviations:** 4 auto-fixed (3 type/lint fixes, 1 testability fix)
**Impact on plan:** All fixes necessary for correctness or test coverage. No scope creep.

## Issues Encountered

- The prior executor wrote `session.py` and `test_session.py` before crashing (all 6 tests were already green). This executor committed those unchanged, then implemented tasks 4 and 5.
- ruff-format pre-commit hook reformatted files on several commit attempts — handled by re-staging after format on each retry.

## Known Stubs

None — all data paths wired to real SQLite and real Anthropic SDK calls (mocked in tests via MockAnthropicClient).

## Next Phase Readiness

- `ResidentAgent`, `AgentMemory`, `SessionManager` are ready for Plan 06-04 (playtest runner)
- `ResidentAgent.system_prompt_text()` is ready for Plan 06-05 (prompt-hash registry per D-14)
- `token-world agent-turn` enables interactive manual stepping before playtest runner is available
- No blockers

---
*Phase: 06-resident-agent-end-to-end-loop*
*Completed: 2026-04-13*
