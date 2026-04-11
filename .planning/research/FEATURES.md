# Feature Landscape

**Domain:** LLM-powered procedural universe simulation
**Researched:** 2026-04-11

## Table Stakes

Features the simulation must have to function. Missing = core loop broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Knowledge graph with arbitrary properties | Core data model. Without flexible schema, new concepts cannot emerge dynamically. | Medium | NetworkX DiGraph with dict attributes. The hard part is the persistence layer, not the graph itself. |
| Mechanic framework (preconditions + side effects) | Mechanics are the rules of the world. Without a framework, generated code has no structure. | Medium | Define a Mechanic protocol with `check(graph, context) -> bool` and `apply(graph, context) -> list[Mutation]`. |
| LLM mechanic generation | The core innovation. Without this, it is just a static rule engine. | High | Structured output to Python code using the framework. Needs good prompt engineering and validation. |
| Simulation engine (action -> mechanic -> observation) | The main loop. Everything else feeds into this. | Medium | Pipeline of LLM calls: classify action, lookup/generate mechanic, execute, format observation. |
| Resident agent with personality | Someone has to inhabit the world. Without an agent, nothing happens. | Low-Medium | Personality as system prompt + memory context. Actions are free-text output. |
| Graph state persistence | Must survive restarts. Core requirement per PROJECT.md. | Medium | SQLite + JSON snapshots. |
| Mechanic persistence and versioning | Must track every mechanic change. Core requirement. | Medium | Mechanics table with version column, mechanic_versions table for history. |
| Graph state snapshots | Enable rollback and replay. Core requirement. | Medium | Periodic full JSON dump + event log for replay. |
| Simulation history log | Track what happened for debugging and replay. | Low | Append-only table: timestamp, agent_action, mechanic_used, graph_mutations, observation_returned. |

## Differentiators

Features that make Token World interesting beyond a basic simulation.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Emergent concept creation | Temperature, hunger, currency appear only when mechanics create them -- not predefined. | Medium | This is the magic. The graph starts nearly empty and grows organically. Requires good mechanic generation prompts. |
| Mechanic coherence checking | When generating a new mechanic, verify it does not contradict existing mechanics. | High | Query existing mechanics that touch the same graph nodes/properties. Include in generation prompt. Defer to v1.1 if too complex. |
| Time-travel debugging | Replay simulation from any snapshot, step through events. | Medium | Event log + snapshots make this straightforward. The persistence layer does the heavy lifting. |
| Grounded observations | All simulation responses derive from graph state, never hallucinated. | Medium | The engine must query the graph and cite specific nodes/properties in its observation. Prompt engineering challenge. |
| Natural language action parsing | Agent says "I pick up the rock" and engine maps to `pickup(agent, rock)` mechanic. | Medium | Classification step before mechanic lookup. Haiku is sufficient for this. |

## Anti-Features

Features to explicitly NOT build in v1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Web UI / dashboard | Premature. Core loop must be proven first. Adds massive scope. | CLI output with rich formatting. Inspect state via Python REPL or click commands. |
| Multi-agent simulation | Requires solving agent-agent interaction, turn ordering, conflict resolution. v2 concern. | Single agent + engine. Prove the loop works for one agent first. |
| Visual output (images, maps) | Text-first simulation. Images are a separate rendering concern. | Rich text descriptions grounded in graph state. |
| Real-time simulation | Adds timing/scheduling complexity. No benefit for proving the core loop. | Turn-based: agent acts, engine responds, repeat. |
| Plugin system for mechanics | Over-engineering. The mechanic framework IS the plugin API. | Generated mechanics use the framework directly. |
| Authentication / multi-user | It is a local hobby project. | Single user, local execution. |
| Distributed graph / sharding | Graph will be tiny for years. | Single SQLite file, single NetworkX instance. |
| Natural language graph queries | Cool but unnecessary. Python graph queries are more precise. | Mechanics use Python API: `graph.nodes[node_id]['temperature']`. |

## Feature Dependencies

```
Knowledge Graph (NetworkX + persistence)
    |
    +---> Mechanic Framework (needs graph query/mutation API)
    |         |
    |         +---> Mechanic Generation (needs framework to generate against)
    |         |         |
    |         |         +---> Simulation Engine (needs mechanics to execute)
    |         |                   |
    |         |                   +---> Resident Agent (needs engine to interact with)
    |         |
    |         +---> Mechanic Versioning (needs mechanics to version)
    |
    +---> Graph State Snapshots (needs graph to snapshot)
    |
    +---> Simulation History Log (needs engine loop to log)
```

## MVP Recommendation

Build in this order (respects dependency chain):

1. **Knowledge graph + persistence** -- Foundation everything else builds on
2. **Mechanic framework** -- Define the API surface for preconditions and side effects
3. **Mechanic execution** -- Execute mechanics against the graph, verify mutations work
4. **LLM mechanic generation** -- Generate mechanics using the framework (the hard part)
5. **Simulation engine** -- Wire up action interpretation + mechanic selection/generation + execution
6. **Resident agent** -- Add personality, memory, and the action loop
7. **Versioning and snapshots** -- Add history tracking after the loop works

**Defer to v1.1:**
- Mechanic coherence checking (complex, needs a body of existing mechanics first)
- Time-travel debugging UI (the data will be there from snapshots; the UI can come later)
- Advanced grounding verification (start with prompt-based grounding, add verification later)
