# Roadmap: Token World

## Overview

Token World is built bottom-up along its hard dependency chain: universe infrastructure as the foundation, then knowledge graph, then mechanic framework, then use-case-informed design validation, then LLM generation, then the simulation engine, then the resident agent closing the loop, and finally the attention/consciousness system that makes the world feel alive. Each phase delivers a testable, observable capability. Testing and autonomy tooling are woven into the phases where their target features are built, not deferred to a separate phase.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 0: Universe Infrastructure** - Universe scaffolding, instance management, CLAUDE.md/MCP generation, harness-agnostic design
- [ ] **Phase 1: Graph Foundation** - Knowledge graph with persistence, snapshots, and test infrastructure
- [ ] **Phase 2: Mechanic Framework** - Protocol, DSL primitives, seed mechanics, versioning, and CLI tooling
- [ ] **Phase 3: Design Validation** - Use case library, gap analysis, optional indexes, and graph visualization
- [ ] **Phase 4: LLM Mechanic Generation** - Code generation, validation, sandboxing, and diagnostics
- [ ] **Phase 5: Simulation Engine** - Action interpretation, mechanic execution, grounded observations, and history
- [ ] **Phase 6: Resident Agent & End-to-End Loop** - Agent with personality and memory, playtesting, quality scoring, regression suite
- [ ] **Phase 7: Attention & Consciousness** - Duration-aware actions and reusable interruption threshold pattern

## Phase Details

### Phase 0: Universe Infrastructure
**Goal**: A universe can be created as a self-contained folder with generated CLAUDE.md, .mcp.json, universe.db, and git versioning — ready for any agent coding harness to operate in
**Depends on**: Nothing (first phase)
**Requirements**: UNIV-01, UNIV-02, UNIV-03, UNIV-04, UNIV-05, UNIV-06
**Success Criteria** (what must be TRUE):
  1. Running create_universe() produces a folder with CLAUDE.md, AGENTS.md symlink, .mcp.json, universe.db, mechanics/, agents/, and initialized git repo
  2. Generated CLAUDE.md contains world rules and tool documentation sufficient for an agent to understand and operate the simulation
  3. Generated .mcp.json exposes simulation tools that an agent coding harness can discover and call
  4. Universe manager can create, load, list, and delete universes
  5. The universe folder works with Claude Code, and is designed to work with other harnesses (Codex, etc.) via AGENTS.md symlink
  6. A tick_summaries/ folder exists inside the universe with hierarchical JSON summaries enabling agent catch-up after compaction or handoff
**Plans:** 2 plans

Plans:
- [x] 00-01-PLAN.md — Project bootstrap, XDG paths, Pydantic models, UniverseManager CRUD, Click CLI
- [x] 00-02-PLAN.md — Universe scaffolding (CLAUDE.md template, AGENTS.md symlink, .mcp.json, MCP stub server, git init, tick_summaries)

### Phase 1: Graph Foundation
**Goal**: A persistent, snapshot-capable knowledge graph exists that supports arbitrary emergent properties and can be rolled back to any previous state
**Depends on**: Phase 0
**Requirements**: GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05, TEST-03, TEST-06, AUTO-01
**Success Criteria** (what must be TRUE):
  1. A graph node can have arbitrary properties added at runtime without any schema declaration, and those properties persist across process restarts
  2. A snapshot can be taken at any point, the graph mutated further, and then restored to the snapshot with all state matching the original
  3. Test helper utilities exist that let tests build graph scenarios in 2-3 lines instead of verbose setup code
  4. CLAUDE.md exists with architecture overview, critical constraints, validation protocols, and script catalog sufficient for an agent to understand the project without human guidance
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Core KnowledgeGraph, identity, models, events, GraphBuilder, and SQLite persistence
- [x] 01-02-PLAN.md — Snapshot/restore with tick-linked IDs, round-trip integrity tests, retention policy
- [x] 01-03-PLAN.md — CLAUDE.md update with architecture, conventions, validation protocols, script catalog

### Phase 2: Mechanic Framework
**Goal**: A stable mechanic protocol exists with DSL primitives, hand-written seed mechanics prove the API works, and all mechanics are versioned and queryable
**Depends on**: Phase 1
**Requirements**: MECH-01, MECH-02, MECH-05, MECH-06, TEST-01, AUTO-03
**Success Criteria** (what must be TRUE):
  1. A mechanic with check() and apply() can query the graph for preconditions and return mutations that modify graph state, using DSL primitives (query_node, query_neighbors, mutate)
  2. At least 3 hand-written seed mechanics (movement, observation, basic interaction) execute correctly against the graph and produce verifiable state changes
  3. Every change to a mechanic is versioned with full history retrievable programmatically
  4. CLI scripts exist for running simulation, inspecting graph state, and listing mechanics without composing raw commands
**Plans:** 3 plans

Plans:
- [x] 02-01-PLAN.md — Core protocol (Mechanic ABC, CheckResult), MechanicContext DSL, matchers, chain execution engine, execution trace
- [x] 02-02-PLAN.md — Seed mechanics (movement, observation, environmental reaction), PyYAML, scaffold integration, chain execution integration tests
- [x] 02-03-PLAN.md — Mechanic registry (folder scanning, git versioning), loader, CLI commands (list-mechanics, run-mechanic, query-graph)

### Phase 3: Design Validation
**Goal**: A use case library covering diverse interaction scenarios exists, gap analysis has informed architecture adjustments, and optional graph indexes are available for mechanics that need them
**Depends on**: Phase 2
**Requirements**: DVAL-01, DVAL-02, GRAPH-06, GRAPH-07, AUTO-04
**Success Criteria** (what must be TRUE):
  1. Use case library covers at least spatial, social, resource, environmental, and edge-case interaction scenarios with concrete action-observation pairs
  2. Gap analysis report identifies missing mechanics or framework capabilities, and each gap has a disposition (address now, defer, out of scope)
  3. Spatial queries via R-tree index and temporal queries via time-range index are available as optional primitives that mechanics can use
  4. Mermaid diagrams can be generated from graph state for visual inspection of world topology
**Plans**: TBD

Plans:
- [x] 03-01: TBD
- [x] 03-02: TBD
- [ ] 03-03: TBD

### Phase 4: LLM Mechanic Generation
**Goal**: The LLM can generate valid, executable Python mechanics from action context, with validation and diagnostics ensuring generated code meets framework requirements
**Depends on**: Phase 3
**Requirements**: MECH-03, MECH-04, TEST-02, AUTO-02
**Success Criteria** (what must be TRUE):
  1. Given an action context with no matching mechanic, the LLM generates a Python mechanic that passes syntax validation, AST checks, and executes successfully against a test graph
  2. Generated mechanics use the framework protocol (check/apply) and DSL primitives, not raw graph manipulation
  3. Multi-mechanic chains execute in sequence and produce correct cumulative state changes verified by integration tests
  4. Each simulation turn can dump system prompts, raw LLM responses, and parsed output to inspectable diagnostic files
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD

### Phase 5: Simulation Engine
**Goal**: The engine interprets text actions, matches or generates mechanics, executes them against the graph, and returns grounded observations -- the full pipeline works end-to-end without a live agent
**Depends on**: Phase 4
**Requirements**: SIM-01, SIM-02, SIM-03, SIM-04, SIM-05, SIM-06, SIM-07, SIM-08, SIM-11
**Success Criteria** (what must be TRUE):
  1. A text action (e.g. "pick up the rock") is classified into a structured action and matched to the correct existing mechanic
  2. When no mechanic exists for an action, the engine triggers generation and the new mechanic executes successfully
  3. Observations returned to the caller contain only information derivable from current graph state -- no hallucinated properties or entities
  4. Observations are contextually filtered so only relevant properties appear (e.g. temperature not shown when examining a keyboard)
  5. Conservation laws are enforced -- mechanics cannot create matter/energy from nothing; attempts produce appropriate failure observations
  6. Per-tick summaries are written to tick_summaries/ after each simulation tick, enabling agent catch-up and context compaction
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD
- [ ] 05-03: TBD

### Phase 6: Resident Agent & End-to-End Loop
**Goal**: A personality-driven agent inhabits the world, the full simulation loop runs autonomously, and automated quality infrastructure validates the experience
**Depends on**: Phase 5
**Requirements**: AGENT-01, AGENT-02, AGENT-03, AGENT-04, DVAL-03, TEST-04, TEST-05, TEST-07, AUTO-05, AUTO-06, AUTO-07, SIM-12
**Success Criteria** (what must be TRUE):
  1. An agent with a randomly generated personality produces text actions that reflect its personality traits and receives observations grounded in graph state
  2. Agent memory persists across sessions and the agent can reference previous experiences coherently
  3. An agent session can be forked from a previous point, creating a divergent simulation timeline
  4. Playtest runner executes N turns (including adversarial/edge-case inputs) and produces structured quality reports with per-turn grounding accuracy and mechanic validity scores
  5. System prompt or instruction changes automatically trigger grounding regression tests, and key use case scenarios from Phase 3 execute as end-to-end integration tests
  6. Hierarchical tick summary compression runs automatically, compacting tick-level summaries into batch and epoch summaries so agent context stays bounded across long simulations
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD
- [ ] 06-03: TBD
- [ ] 06-04: TBD

### Phase 7: Attention & Consciousness
**Goal**: Long-running actions and consciousness states use a single composable interruption threshold pattern, making the simulation feel temporally alive
**Depends on**: Phase 6
**Requirements**: SIM-09, SIM-10
**Success Criteria** (what must be TRUE):
  1. Long-running actions skip boring intermediate turns and only interrupt the agent when significance exceeds the current attention threshold
  2. Sleep, daydreaming, and autopilot travel all use the same interruption threshold infrastructure, demonstrating the pattern's composability
  3. An agent traveling a long distance experiences compressed time with interruptions only for significant events (demonstrating both SIM-09 and SIM-10 working together)
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Universe Infrastructure | 0/2 | Planning complete | - |
| 1. Graph Foundation | 0/3 | Planning complete | - |
| 2. Mechanic Framework | 0/3 | Planning complete | - |
| 3. Design Validation | 0/3 | Not started | - |
| 4. LLM Mechanic Generation | 0/3 | Not started | - |
| 5. Simulation Engine | 0/3 | Not started | - |
| 6. Resident Agent & End-to-End Loop | 0/4 | Not started | - |
| 7. Attention & Consciousness | 0/2 | Not started | - |
