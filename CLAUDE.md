<!-- GSD:project-start source:PROJECT.md -->
## Project

**Token World**

## Agent Autonomy

Act as autonomously as possible. Minimize human steering — plan and execute without asking for confirmation on routine decisions. Specifically:

- **Bias toward action.** If the path forward is clear, take it. Don't ask "should I proceed?" — just proceed.
- **Make reasonable decisions.** When a choice isn't covered by existing decisions (PROJECT.md, CONTEXT.md), pick the pragmatic option and document what you chose. Only escalate genuinely ambiguous or high-stakes decisions.
- **Self-correct.** If something breaks, diagnose and fix it. Only surface problems you've tried and failed to resolve.
- **Challenge decisions when rationale exists.** Documented rationale is there so it can be questioned as circumstances change. If a prior decision's reasoning no longer holds, flag it rather than blindly following.

## Operating Principles

1. **Close the feedback loop** — Don't write and assume. Push and check CI. Run tests. Hit the endpoint. Render the page. Take the screenshot. Get real feedback from the environment before declaring done. If CI is "set up," it must be passing. If a page is "deployed," it must be loading.
2. **Aggressive subagent delegation** — Coordinating agents must delegate research, implementation, and validation to subagents to prevent context fill. Never let the orchestrator do work a subagent could do.
3. **ROI awareness** — If implementation seems very complex for the value it brings, something is wrong. Ask: are we missing convenience utilities that would make things simpler?
4. **Self-improving infrastructure** — CLAUDE.md must be comprehensive. Tooling must scale with the project. After completing work, ask: is grounding sufficient? Do agents have the tools, instructions, and validation they need?
5. **Reversibility enables boldness** — Worktrees for exploring directions that can be reverted. Graph snapshots for rolling back corruption. If every action is reversible, agents can make bolder moves without human approval.
6. **Ground truth obsession** — If it's not in a committed artifact (code, tests, docs, plans), it's not real. No side channels, no implicit state, no hallucinated results. Verify against the real environment, not assumptions.
7. **Dogfooding** — Tools built for the simulation (graph visualization, trace replay, diagnostics) must also serve agents building the project. Don't build "dev tools" and "simulation tools" separately.
8. **Composition over specialization** — Prefer composable primitives that combine in surprising ways over purpose-built features. One generic mechanic pattern (interruption thresholds) handles sleep, daydreaming, autopilot travel, drunkenness. This is the simulation's core philosophy and the project's engineering philosophy.
9. **Graph is ground truth** — If it's not in the graph, it doesn't exist. No side channels, no implicit state, no LLM-hallucinated state. All simulation responses must derive from knowledge graph state and mechanic execution.

## Documentation Maintenance

- Maintain `docs/` with subfolders: `design/` (architecture, Mermaid diagrams, technical decisions) and `guides/` (user-facing how-tos, setup, contributing)
- Store diagrams as **Mermaid in markdown** — never check in rendered PNGs. Render on-demand with the mermaid MCP when visual review is needed.
- Link generously between docs to avoid duplication
- Update Mermaid diagrams in `docs/design/` when architecture changes
- Keep docs attractive for potential contributors — clear README, design rationale, visual architecture diagrams
- See [docs/design/architecture.md](docs/design/architecture.md) for system component diagrams
- New tooling/UX features must declare their primary surface per [docs/design/tooling-surfaces.md](docs/design/tooling-surfaces.md)

## Code Quality

- Use `prek` for pre-commit hooks (linting/formatting via ruff) — preferred over `pre-commit`
- Use `uv` for package management
- Use `ruff` for linting and formatting
- Use `mypy` for type checking on the mechanic framework API

A universe simulator where LLM-powered agents inhabit a text-based world and interact with an environment whose rules are procedurally generated on-the-fly. The simulation engine — itself an LLM agent — interprets resident agent actions, maps them to existing mechanics or generates new ones, and returns grounded observations. All world state lives in a flexible knowledge graph that evolves as new concepts emerge.

**Core Value:** The simulation engine reliably interprets agent actions, generates coherent mechanics as executable Python code, and maintains a consistent knowledge graph — so from a resident agent's perspective, the world feels fully real.

### Constraints

- **Language**: Python — engine, framework, and generated mechanics all in Python
- **Knowledge Graph**: Schema-less/flexible — must accommodate arbitrary properties and relations without migrations
- **Persistence**: Full state persistence — graph, mechanics, agent memory, history must survive restarts
- **Budget**: Hobby project — prefer cost-efficient LLM usage; start with capable models, optimize later
- **Grounding**: All simulation responses must derive from knowledge graph state and mechanic execution — no ungrounded LLM generation in observations
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

Python 3.12+, NetworkX (in-memory graph), SQLite (persistence), Anthropic SDK (LLM).
Hybrid agent architecture: Agent SDK (Opus) at operator layer for mechanic generation + human collaboration; raw Anthropic Python SDK inside simulation tools for deterministic pipeline calls (Haiku for classification, Sonnet for observation).
Simulation exposed as MCP tools: `resume_tick`, `rollback`, `list_mechanics`.
No sandboxing for v1; add RestrictedPython if needed.

**Do not use:** LangChain, MongoDB, Neo4j, FastAPI/Flask, LangGraph, CrewAI, Celery, SQLAlchemy ORM, pickle.

See [.planning/research/STACK.md](.planning/research/STACK.md) for full stack tables, alternatives considered, model selection strategy, persistence architecture, and installation commands.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

- **Graph mutations:** Always through `KnowledgeGraph` methods (`add_node`, `add_edge`, `set`, `remove_node`, `remove_edge`). Never direct NetworkX access.
- **Node types:** Only `"agent"` and `"entity"`. Everything else is emergent properties.
- **Property values:** Must be JSON-serializable: `str, int, float, bool, None, list, dict`. No custom objects, sets, tuples, bytes. Enforced by `ALLOWED_PROPERTY_TYPES`.
- **Node IDs:** Use `kg.claim_id("name")` to get a unique, human-readable ID. Never hardcode IDs that might collide.
- **Snapshots:** Linked to tick IDs. Summary describes changes since last snapshot. Max 50 retained.
- **SQLite:** Raw `sqlite3` with parameterized queries. No ORM. Context manager pattern: `with sqlite3.connect(str(path)) as conn:`.
- **Testing:** `GraphBuilder` in `tests/test_graph/conftest.py` for fluent graph construction. Use `kg` fixture for KnowledgeGraph with temp DB. Use `graph_builder` fixture for builder pattern.
- **Imports:** Use `from token_world.graph import KnowledgeGraph, Mutation` (public API via `__init__.py`).
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

### Graph Module (`src/token_world/graph/`)

The knowledge graph is the ground truth for all simulation state. All mutations go through the `KnowledgeGraph` API to ensure event logging, property validation, and persistence correctness.

- **`knowledge_graph.py`** -- `KnowledgeGraph` class wrapping NetworkX DiGraph. All mutations logged as events. Two node types: `agent` and `entity` (D-01). Query API (`query`, `has_node`, `has_edge`, `neighbors`, `nodes`) and Mutation API (`add_node`, `add_edge`, `set`, `remove_node`, `remove_edge`). Every mutation returns a `Mutation` dataclass. `claim_id()` for readable unique IDs (D-02).
- **`persistence.py`** -- `GraphPersistence` SQLite adapter. Stores graph as JSON blob via `json_graph.node_link_data`. Manages `graph_state` and `graph_events` tables. Lazy table creation on first `save()`.
- **`events.py`** -- `GraphEvent` frozen dataclass and `EventStore`. All mutations produce events with tick ID, event type, target, old/new values for audit trail.
- **`identity.py`** -- `claim_id()` deconfliction. Proposes readable ID, appends progressive SHA-256 hash suffix on collision (`"wallet"` -> `"wallet_a7"` -> `"wallet_a7z6"`).
- **`models.py`** -- `Mutation` and `SnapshotInfo` frozen dataclasses. `ALLOWED_PROPERTY_TYPES` constant defining `(str, int, float, bool, type(None), list, dict)`.

### Universe Module (`src/token_world/universe/`)

UniverseManager for creating/managing universe instances. Each universe is a self-contained folder with CLAUDE.md, .mcp.json, universe.db, mechanics/, agents/. Scaffolding via Jinja2 templates.

### Key Invariant

All graph mutations go through `KnowledgeGraph` API methods. Never call `nx.DiGraph` methods directly. This ensures event logging, property validation, and persistence correctness.

See [docs/design/architecture.md](docs/design/architecture.md) for system component diagrams.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

## Validation Protocols

- **Quick test:** `uv run pytest tests/ -x -q` (stop on first failure)
- **Full test:** `uv run pytest -v` (verbose, all tests)
- **Graph tests only:** `uv run pytest tests/test_graph/ -x -q`
- **Lint:** `uv run ruff check src/`
- **Format check:** `uv run ruff format --check src/`
- **Format fix:** `uv run ruff format src/`
- **Type check:** `uv run mypy src/token_world/graph/`

Run quick test after every change. Run full suite before commits.

## Script Catalog

| Command | Purpose |
|---------|---------|
| `token-world create "Name"` | Create a new universe with scaffolding |
| `token-world list` | List all universes with metadata |
| `token-world delete slug` | Delete a universe |
| `token-world playtest <slug> [--turns N] [--judge]` | Run N-turn simulation, write JSON report; add `--judge` for Sonnet rubric |
| `token-world cost <slug> [--since N] [--format table\|json]` | Aggregate per-universe LLM cost + token counts from `tick_summaries/`; auto-detects backend (anthropic-sdk / claude-cli / mixed) |
| `token-world inspect <slug> [--last N] [--format table\|json]` | Universe-at-a-glance: graph shape, mechanic count by author, recent ticks, active LRAs, recent yields. See `docs/guides/operator-cli.md` |
| `token-world tick <slug> <tick_id> [--format table\|json]` | Pretty-print a single tick's full action -> classification -> mechanic -> mutations -> observation tree |
| `token-world trace <slug> <node_id> <property> [--hops N] [--format table\|json]` | Causal-chain walker: walk `graph_events` backward, enrich each hop with surrounding tick context |
| `token-world mechanics <slug> [--author seed\|operator] [--format table\|json]` | Registry browser with call counts + last-invoked tick |
| `token-world stats <slug> [--since N] [--stream] [--format table\|json]` | Aggregate metrics: throughput, yield rate, novel-mechanic rate, conservation violations, cost (composes with `cost`) |
| `token-world watch <slug> [--interval S]` | Live tail of new tick summaries, one line per tick (Ctrl-C to exit) |
| `token-world agents <slug> [--id X] [--format table\|json]` | Inspect agent-typed nodes: personality, persona, memory, active LRA, attention state |
| `token-world diff <slug> <tick_a> <tick_b> [--format table\|json]` | Graph changes between two ticks: nodes/edges added or removed + property old -> new |
| `token-world dashboard <slug> [--port 8080] [--no-show] [--no-dark]` | Launch the read-only NiceGUI web dashboard — 4 panels (stats strip, live tick stream, graph canvas, causal chain). Requires `uv sync --extra dashboard`. See `docs/guides/dashboard.md` |
| `TOKEN_WORLD_BACKEND=claude-cli token-world playtest ...` | Route LLM calls through `claude -p` subprocess (zero marginal cost via Claude subscription) — see `docs/guides/claude-cli-backend.md` |
| `uv run pytest -x -q` | Quick test run |
| `uv run pytest -v` | Full verbose test run |
| `uv run ruff check src/` | Lint check |
| `uv run ruff format src/` | Auto-format |
| `uv run mypy src/token_world/graph/` | Type check graph module |
| `uv run mypy src/token_world/inspect/` | Type check inspect (operator CLI) module |
| `uv run python scripts/phase_waves.py <phase>` | Report wave structure + files_modified overlap for a phase (pre-execution safety check) |
| `uv run python scripts/inspect_playtest_report.py <path>` | Pretty-print a playtest report JSON: turns, aggregate scores, judge block |
| `uv run python scripts/update_prompt_hashes.py <universe_slug>` | Refresh `<universe>/prompts.sha256.json` baseline after reverting experimental prompt edits (preserves personality-bound `agent_system_prompt` hash) |
| `scripts/commit.sh <msg-file>` | 3-line wrapper for `git add -A && git commit -F <msg> && git push origin master` — sidesteps the `deny-ad-hoc-bash` 300-char heredoc block |
| `uv run python scripts/check_requirements_traceability.py [--milestone v1.0\|active]` | Diff REQUIREMENTS.md status against ROADMAP/Traceability table; non-zero on drift; pytest-wired in `tests/test_meta/` |
| `uv run python scripts/check_roadmap_progress.py [--milestone v1.0\|active]` | Diff ROADMAP Progress table against actual phase PLAN/SUMMARY counts; non-zero on drift; pytest-wired in `tests/test_meta/` |
| `uv run python scripts/run_uat.py <slug> [--turns N]` | Phase 6 UAT in one command — runs all 3 items end-to-end via claude-cli backend; prints verdict |
| `uv run python scripts/phase_show.py <N>` | Print CONTEXT + PLAN titles + SUMMARY headlines + VERIFICATION status for a phase (handles `04.1`, `5`, `07.1`, etc.) |
| `uv run python scripts/ci_status.py [--since SHA\|tag]` | Compact CI status: green/red per commit since `<ref>` plus links to failing job logs |

## Bash Hygiene for Agents

A few rough edges worth knowing:

- **Use absolute paths, not `$HOME`** — a Claude Code permission-prompt bug mis-handles `$HOME` in commands, rejecting tool uses that would otherwise auto-approve. Write `/home/reuben/.claude/...` explicitly. Same applies to `~/`.
- **Avoid inline `python3 -c` / heredoc pipelines** — they look opaque in permission prompts and aren't reviewable after the fact. If you need to parse JSON, pipe to `jq`. If the logic is more than a one-liner, promote it to a script in `scripts/` (see `phase_waves.py` for the pattern).
- **Avoid long chained pipelines that assert invariants** — if bash is computing something you'll want to re-run later, it belongs in a committed `scripts/` file (grounding rule #4, "ad-hoc bash is a missing-tool signal").
- **Use `scripts/commit.sh <msg-file>` for commits** — 3-line wrapper for `git add -A && git commit -F <msg-file> && git push origin master`. Avoids the `deny-ad-hoc-bash.js` hook that blocks 300+ char bash commands with inline heredocs. Write the commit body to a unique path under `/tmp/commit_<topic>.txt` (the `Write` tool refuses to overwrite unread files, so reusing `/tmp/commit_msg.txt` across sessions fails).

## Critical Constraints

1. **Graph is ground truth** -- If it's not in the KnowledgeGraph, it doesn't exist. No side channels, no implicit state.
2. **Mutation-mediated access** -- All graph changes go through KnowledgeGraph API. This ensures event logging, validation, and persistence correctness. Direct NetworkX DiGraph access breaks these guarantees.
3. **Two node types only** -- Framework enforces `agent` and `entity`. All other classification is emergent (mechanics add properties like `subtype="weapon"`).
4. **JSON-serializable properties** -- Property values must survive `json.dumps/loads` roundtrip. No Python-specific types (set, tuple, bytes, custom objects).
5. **Snapshot-linked ticks** -- Every snapshot references a tick ID. Rollback restores to a tick's state. Events before oldest snapshot may be compacted.
6. **No ORM** -- Raw sqlite3 only. SQLAlchemy is explicitly forbidden.
7. **No pickle** -- All serialization via JSON. Pickle is explicitly forbidden.

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
