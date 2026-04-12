# Token World

## What This Is

A universe simulator where LLM-powered agents inhabit a text-based world and interact with an environment whose rules are procedurally generated on-the-fly. The simulation engine — itself an LLM agent — interprets resident agent actions, maps them to existing mechanics or generates new ones, and returns grounded observations. All world state lives in a flexible knowledge graph that evolves as new concepts emerge.

## Core Value

The simulation engine reliably interprets agent actions, generates coherent mechanics as executable Python code, and maintains a consistent knowledge graph — so from a resident agent's perspective, the world feels fully real.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Knowledge graph with flexible schema that supports arbitrary properties and relations
- [ ] Mechanic framework providing primitives for preconditions (graph queries) and side effects (graph mutations)
- [ ] LLM-powered mechanic generation that produces executable Python code using the framework
- [ ] Simulation engine that maps resident agent text output to existing mechanics or triggers new mechanic creation
- [ ] Resident agent with randomly generated personality that interacts with the environment via text
- [ ] Core simulation loop: agent action → engine interpretation → mechanic execution → observation returned
- [ ] Full persistence of graph state, mechanics, agent memory/personality, and simulation history
- [ ] Mechanic versioning so every change to a mechanic is tracked
- [ ] Graph state snapshots for rollback and replay

### Out of Scope

- Game adaptation / playable game — v1 is a simulation, not a game
- Dashboard / HMI visualization — deferred to v2+ after core loop is proven
- Review agents / bird's eye monitoring — requires multi-agent which is v2+
- Multi-agent scaling (hundreds/thousands) — v1 is single agent + engine
- Multimodal output (images) — text-first, visuals later
- Civic simulation scenarios (UBI, economics) — requires mature mechanics ecosystem
- Contributor onboarding / CI/CD / MkDocs — premature until core is stable
- 8-bit graphics generation — deferred visual enhancement

## Context

- Hobby project driven by the idea that LLMs make truly procedural rule generation feasible
- Inspired by text RPGs but focused on simulation fidelity rather than gameplay
- The knowledge graph must support concepts being introduced dynamically — e.g., temperature doesn't exist until a mechanic creates it, then it becomes a property on relevant nodes
- Mechanics are pairs of preconditions and side effects, implemented as generated Python code using an engine framework (DSL-like primitives for graph queries and mutations)
- The simulation engine must always ground its responses in the knowledge graph — no hallucinated state
- Agent framework: Raw Anthropic Python SDK. The simulation engine is a deterministic orchestrator needing per-call model routing and precise prompt control — not an autonomous agent loop. Thin custom session persistence for agent memory.
- Mechanic sandboxing deferred for v1 (hobby project); add RestrictedPython if issues arise
- Cost efficiency matters for future scaling — model choice per agent role should be considered

## Constraints

- **Language**: Python — engine, framework, and generated mechanics all in Python
- **Knowledge Graph**: Schema-less/flexible — must accommodate arbitrary properties and relations without migrations
- **Persistence**: Full state persistence — graph, mechanics, agent memory, history must survive restarts
- **Budget**: Hobby project — prefer cost-efficient LLM usage; start with capable models, optimize later
- **Grounding**: All simulation responses must derive from knowledge graph state and mechanic execution — no ungrounded LLM generation in observations

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python for engine and mechanics | Rich AI/ML ecosystem, easy LLM code generation, networkx available for graphs | -- Pending |
| Generated code mechanics (not declarative rules) | Full expressiveness; framework provides structure while code gives flexibility for complex mechanics | -- Pending |
| Flexible schema-less knowledge graph | New concepts (temperature, inventory, routes) must emerge dynamically as mechanics create them | -- Pending |
| Single agent + engine for v1 | Prove the core loop works before scaling to multi-agent | -- Pending |
| Full persistence from the start | Enables time-travel debugging, rollback, and replay — foundational for tooling vision | -- Pending |
| Raw Anthropic Python SDK (not Claude Code SDK) | Deterministic engine loop needs per-call model routing, precise prompt control, and no subprocess overhead. Thin custom session persistence (~50-100 LOC) for agent memory. Claude Code SDK's autonomous loop conflicts with the controlled simulation pipeline. | -- Pending |
| Mechanics as git-versioned folders (not DB-stored code) | Each mechanic is a folder with mechanic.py, tests/, and meta.yaml. Git provides versioning (commit hashes, diff, blame) for free. Registry is a lightweight index referencing folders, not a database storing code blobs. Inspectable, testable, dogfooding-friendly. | -- Pending |
| No sandboxing for v1 | Hobby project; add RestrictedPython when scaling or if issues arise | -- Pending |
| Opus for mechanic generation, Sonnet/Haiku for engine classification | Code generation quality justifies Opus; action classification is simpler | -- Pending |

## Operating Principles

These principles govern how agents work on this project autonomously:

1. **Aggressive subagent delegation** — Coordinating agents must delegate research, implementation, and validation to subagents to prevent context fill. Never let the orchestrator do work a subagent could do.
2. **ROI awareness** — If a feature implementation seems very complex for the value it brings, something is wrong. Applies to tests too: thousands of tests add value but may be expensive to maintain. Ask: are we missing convenience utilities (graph builders, test helpers) that would make things simpler and more concise?
3. **Self-improving infrastructure** — Three reinforcing facets:
   - *Context engineering & grounding* — CLAUDE.md must be comprehensive. Tooling (diagnostics, visualizations, playtests, metrics) must scale with the project. If grounding is insufficient, the project stalls waiting for human course correction.
   - *Dogfooding* — Tools built for the simulation (graph visualization, trace replay, diagnostics) must also serve agents building the project. Don't build "dev tools" and "simulation tools" separately. If an agent implementing the engine can use the graph visualizer to debug its own work, that's leverage compounding.
   - *Continuous retrospective* — After each phase, ask: is grounding sufficient? Do we have more leverage than before? Are agents performing well? Do they need better tools, instructions, or validation? The grounding infrastructure must grow with the features.
4. **Composition over specialization** — Prefer composable primitives that combine in surprising ways over purpose-built features. One generic mechanic pattern (interruption thresholds) handles sleep, daydreaming, autopilot travel, drunkenness. This is the simulation's core philosophy and the project's engineering philosophy.
5. **Reversibility enables boldness** — Worktrees for exploring directions that can be reverted. Graph snapshots for rolling back corruption. Session forks for undoing agent state. If every action is reversible, agents can make bolder moves without human approval. Invest in undo infrastructure early.
6. **Ground truth obsession** — If it's not in the graph, it doesn't exist. No side channels, no implicit state, no LLM-hallucinated state. Applies to the simulation AND the project itself — if it's not in a committed artifact (requirements, plans, tests), it's not real.

## Documentation

- Maintain `docs/` with two subfolders: `design/` (architecture, Mermaid diagrams, technical decisions) and `guides/` (user-facing how-tos, setup, contributing)
- Store diagrams as Mermaid in markdown — never check in rendered PNGs. Render on-demand with the mermaid MCP when visual review is needed.
- Link generously between docs to avoid duplication
- Keep docs attractive for potential contributors — clear README, design rationale, visual architecture diagrams
- Design docs should evolve with the codebase — update Mermaid diagrams when architecture changes

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-11 after initialization*
