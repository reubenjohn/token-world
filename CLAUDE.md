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
Simulation exposed as MCP tools: `resume_tick`, `rollback`, `list_mechanics`, `register_mechanic`.
No sandboxing for v1; add RestrictedPython if needed.

**Do not use:** LangChain, MongoDB, Neo4j, FastAPI/Flask, LangGraph, CrewAI, Celery, SQLAlchemy ORM, pickle.

See [.planning/research/STACK.md](.planning/research/STACK.md) for full stack tables, alternatives considered, model selection strategy, persistence architecture, and installation commands.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

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
