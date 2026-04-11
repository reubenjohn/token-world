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
- Agent framework selection (Claude Agent SDK, LangGraph, raw API calls) is an open research question
- Mechanic sandboxing strategy (isolated execution vs trust + rollback) needs research
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
