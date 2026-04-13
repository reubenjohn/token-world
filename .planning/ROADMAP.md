# Roadmap: Token World

## Overview

Token World is built bottom-up along its hard dependency chain: universe infrastructure as the foundation, then knowledge graph, then mechanic framework, then use-case-informed design validation, then mechanic authoring & validation infrastructure (supersedes the originally-planned "LLM generation pipeline" — the top-level coding agent is the mechanic author; the framework provides the gate, not the generator), then the simulation engine, then the resident agent closing the loop, and finally the attention/consciousness system that makes the world feel alive. Each phase delivers a testable, observable capability. Testing and autonomy tooling are woven into the phases where their target features are built, not deferred to a separate phase.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 0: Universe Infrastructure** - Universe scaffolding, instance management, CLAUDE.md/MCP generation, harness-agnostic design
- [x] **Phase 1: Graph Foundation** - Knowledge graph with persistence, snapshots, and test infrastructure
- [x] **Phase 2: Mechanic Framework** - Protocol, DSL primitives, seed mechanics, versioning, and CLI tooling (NOTE: D-15 folder-per-mechanic layout superseded by Phase 4; seeds flatten in plan 04-01)
- [x] **Phase 3: Design Validation** - Use case library (35 UCs across spatial/social/resource/environmental/edge-case), gap analysis (GAP-ANALYSIS.md / GAP-HANDOFF.md), optional spatial + temporal indexes, filtered Mermaid graph visualization
- [x] **Phase 4: Mechanic Authoring & Validation Infrastructure** - Flat mechanic layout (supersedes folder-per-mechanic), validation pipeline, diagnostics substrate, integration-test harness, authoring guides, and seed mechanic authoring waves (MECH01–MECH27) — so the top-level coding agent (Opus via Agent SDK) authors mechanics as normal Python SDLC
- [x] **Phase 5: Simulation Engine** - Action classification (Haiku), mechanic matching, execution, grounded observation synthesis (Sonnet), conservation enforcement, tick summaries. Under inversion of control: when no mechanic matches, the engine yields to the operator — it does NOT generate code. (completed 2026-04-13)
- [x] **Phase 6: Resident Agent & End-to-End Loop** - Agent with personality and memory, playtesting, quality scoring, regression suite (completed 2026-04-13)
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
**Plans:** 7 plans

Plans:
- [x] 03-01-PLAN.md — Wave-0 scaffolding (use-cases directory layout, manifest schema, shared fixtures)
- [x] 03-02-PLAN.md — Spatial index (R-tree via rtree library on MechanicContext)
- [x] 03-03-PLAN.md — Temporal index (EventStore-backed time-range queries, find_state_at_tick)
- [x] 03-04-PLAN.md — viz-graph CLI (Mermaid emission with ego-graph filtering, label escaping)
- [x] 03-05-PLAN.md — Use-case manifest loader (YAML frontmatter parser, schema validation)
- [x] 03-06-PLAN.md — Authoring spatial use cases (UC-S01..UC-S07)
- [x] 03-07-PLAN.md — Authoring social use cases (UC-O01..UC-O08)
- [x] 03-08-PLAN.md — Authoring resource use cases (UC-R01..UC-R07)
- [x] 03-09-PLAN.md — Authoring environmental use cases (UC-V01..UC-V07)
- [x] 03-10-PLAN.md — Authoring edge-case use cases (UC-E01..UC-E06)
- [x] 03-11-PLAN.md — Category aggregation (5 CATEGORY-SUMMARY.md files)
- [x] 03-12-PLAN.md — Gap analysis synthesis (GAP-ANALYSIS.md, GAP-HANDOFF.md, deferred-items.md)

### Phase 4: Mechanic Authoring & Validation Infrastructure
**Goal**: The universe acts as a codebase that the top-level coding agent (Opus via Agent SDK) authors with normal SDLC. Phase 4 delivers the flat mechanic layout (supersedes Phase 2 folder-per-mechanic), a validation gate (syntax → AST → import → contract → tests → dry-execute), a diagnostics substrate ready for Phase 5 to populate, an integration-test harness built on Phase 3 use-case manifests, and authoring guides. "LLM mechanic generation" = operator-driven SDLC; no bespoke generation pipeline is built.
**Depends on**: Phase 3
**Requirements**: MECH-03, MECH-04, TEST-02, AUTO-02 (and revises MECH-05/MECH-06/UNIV-03 to match the flat layout and 3-tool MCP surface)
**Success Criteria** (what must be TRUE):
  1. Mechanics authored by the operator pass the validation pipeline (AST rules forbid raw graph access, `eval/exec/__import__`, `networkx` imports; require Mechanic subclass with id/description/check/apply); invalid mechanics are rejected with structured diagnostics and skipped by the registry
  2. Mechanics use only the framework protocol (check/apply) and `MechanicContext` DSL; AST enforcement guarantees this without relying on reviewer discipline
  3. Multi-mechanic chains execute correctly, verified by the integration-test harness parametrized from Phase 3's use-case action-observation manifests
  4. Per-tick diagnostics folders capture prompts, raw LLM responses, parsed output, execution traces, mutations, and observation synthesis; schema is versioned and populated via a shared `DiagnosticsSink` API ready for Phase 5 wiring


Plans (12 plans):
- [x] 04-01-PLAN.md — Flatten mechanic layout + 3-tool MCP surface + Phase 3 H-01/M-04 fixes
- [x] 04-02-PLAN.md — Validation pipeline (6 stages) + validate-mechanic CLI + registry auto-scan
- [x] 04-03-PLAN.md — Diagnostics substrate (DiagnosticsSink + schema + prune-diagnostics CLI)
- [x] 04-04-PLAN.md — Integration test harness (parametrized from 35 UCs; tri-state outcomes)
- [x] 04-05-PLAN.md — Authoring guide + scaffold-mechanic CLI + framework-gap-stub convention
- [x] 04-06-PLAN.md — Seed cluster: spatial movement extensions (MECH01 passage_move, MECH05 terrain_move, MECH06 position_sync)
- [x] 04-07-PLAN.md — Seed cluster: spatial queries + speak + try_door (MECH02/03/04/13/27)
- [x] 04-08-PLAN.md — Seed cluster: object interaction (MECH07 trade, MECH08 give, MECH14 craft, MECH15 consume, MECH16 pickup)
- [x] 04-09-PLAN.md — Seed cluster: social/belief + framework-gap stubs (MECH10/11/25 + MECH09/MECH12 stubs)
- [x] 04-10-PLAN.md — Seed cluster: resource durability + fungible currency (MECH17 degrade, MECH18 fungible_pay)
- [x] 04-11-PLAN.md — Seed cluster: environmental family (MECH20/22/23/24 + MECH21 stub)
- [x] 04-12-PLAN.md — Phase gate: VALIDATION.md finalization + retrospective

### Phase 04.1: Operator Agent Harness (INSERTED)

**Goal:** The operator — the concrete realisation of PROJECT.md's Hybrid-SDK operator layer — exists as a working Agent-SDK-driven harness that catches yield signals from the simulation, spawns an Opus mechanic-authoring subagent, validates via Phase 4's pipeline, and resumes the tick. Works identically from an interactive Claude Code session inside a universe folder and from a programmatic Agent SDK driver (the latter unblocks Phase 6's playtest runner).
**Depends on:** Phase 4
**Requirements**: AUTO-02 (diagnostics — operator namespace extension), UNIV-03 (3-tool MCP surface — preserved)

> **Scope clarification:** AGENT-03 (agent memory persists across sessions) and AGENT-04 (session forking for rollback) remain Phase 6 per REQUIREMENTS.md. Phase 4.1 delivers the operator-side *infrastructure* those Phase 6 capabilities will build on (YieldSignal contract, operator harness, diagnostics namespace, `rollback` MCP tool whitelisting in the outer SDK session) — not coverage of those requirements themselves. The Phase 6 agent sessions and session-forking work is what actually satisfies AGENT-03/AGENT-04.
**Success Criteria** (what must be TRUE):
  1. A fabricated yield signal from a test-only engine stub triggers the harness to spawn an Opus subagent; the subagent authors a valid mechanic; validation passes; `resume_tick` picks up the new mechanic and the tick completes — all autonomously, no human steps
  2. The same yield→author→resume loop completes from an interactive Claude Code session inside a universe folder, using only the 3-tool MCP surface and the universe's CLAUDE.md guidance
  3. A structured `YieldSignal` dataclass is defined as the contract between engine and operator; its shape is what Phase 5 will emit and 4.1's engine stub fabricates
  4. CLI commands `run-tick`, `inspect-yield`, `resume-tick`, `replay-tick` work against a universe and render diagnostics from Phase 4's substrate (extended with an operator subfolder)
  5. The throwaway engine stub is clearly isolated (imports only from tests or a `testing` module); swapping in the real Phase 5 engine requires no operator-code changes
**Plans:** 5/5 plans complete

Plans:
- [x] 04.1-01-PLAN.md — YieldSignal contract + EngineStub + Wave-0 test scaffolding (claude-agent-sdk dep, integration marker)
- [x] 04.1-02-PLAN.md — Operator diagnostics namespace (extends Phase 4 DiagnosticsSink with operator/ subfolder; write + read APIs)
- [x] 04.1-03-PLAN.md — Operator harness core (Agent SDK driver + mechanic-author subagent + validation @tool + real-Opus integration test)
- [x] 04.1-04-PLAN.md — Dev-UX CLI (run-tick, inspect-yield, resume-tick, replay-tick on the existing token-world Click group)
- [x] 04.1-05-PLAN.md — Interactive entry-point polish (universe CLAUDE.md Operator Flow + .claude/agents/mechanic-author.md scaffold + VALIDATION.md finalisation + architecture diagram)

### Phase 5: Simulation Engine
**Goal**: The engine interprets text actions, routes them to mechanics (or yields to the operator when none match), executes selected mechanics, and returns grounded observations — the full pipeline works end-to-end without a live agent. Under the inversion-of-control model established in Phase 4, the engine NEVER generates code; when no mechanic matches, it halts the tick and yields to the operator, which authors the needed mechanic via normal SDLC before the tick resumes.
**Depends on**: Phase 4.1
**Requirements**: SIM-01, SIM-02, SIM-03, SIM-04, SIM-05, SIM-06, SIM-07, SIM-08, SIM-11 (plus absorbs the Phase-5 half of GAP-ENG16 per 04-CONTEXT.md D-34)
**Success Criteria** (what must be TRUE):
  1. A text action (e.g. "pick up the rock") is classified into a structured action (Haiku) and matched to the correct existing mechanic; classifier returns `no_viable_action` for nonsense rather than triggering yield
  2. When no mechanic matches a well-formed action, the engine halts the tick with a structured yield signal ("no mechanic for: <classified-action>"); after the operator authors + validates the needed mechanic, a subsequent `resume_tick` picks up the new mechanic (registry auto-scan) and completes the tick
  3. Observations returned to the caller contain only information derivable from current graph state — no hallucinated properties or entities
  4. Observations are contextually filtered so only relevant properties appear (e.g. temperature not shown when examining a keyboard)
  5. Conservation laws are enforced — mechanics cannot create matter/energy from nothing; attempts produce appropriate failure observations
  6. Per-tick summaries are written to tick_summaries/ after each simulation tick, enabling agent catch-up and context compaction
  7. Classifier, matcher, and observer LLM calls write prompts, raw responses, and parsed output to the Phase 4 diagnostics substrate (AUTO-02 fully wired end-to-end)
**Plans:** 7 plans

Plans:
- [x] 05-01: TBD
- [x] 05-02: TBD
- [x] 05-03: TBD

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
**Plans:** 7/7 plans complete

Plans:
- [x] 06-00-PLAN.md — Wave-0 prep: TickResult.projected_state field for groundedness scoring
- [x] 06-01-PLAN.md — ResidentAgent module: personality, memory, sessions, agent-turn CLI
- [x] 06-02-PLAN.md — TickCompressor: online batch + epoch hierarchical tick-summary compression
- [x] 06-03-PLAN.md — Use-case regression suite: 35 Phase-3 UC manifests as E2E integration tests
- [x] 06-04-PLAN.md — PlaytestRunner CLI + quality scoring rubric (bundled)
- [x] 06-05-PLAN.md — Prompt-hash registry + automatic regression trigger + optional Sonnet judge
- [x] 06-06-PLAN.md — Adversarial scenario pack + expanded AdversarialBank

### Phase 7: Attention & Consciousness
**Goal**: Long-running actions and consciousness states use a single composable interruption threshold pattern, making the simulation feel temporally alive
**Depends on**: Phase 6
**Requirements**: SIM-09, SIM-10
**Success Criteria** (what must be TRUE):
  1. Long-running actions skip boring intermediate turns and only interrupt the agent when significance exceeds the current attention threshold
  2. Sleep, daydreaming, and autopilot travel all use the same interruption threshold infrastructure, demonstrating the pattern's composability
  3. An agent traveling a long distance experiences compressed time with interruptions only for significant events (demonstrating both SIM-09 and SIM-10 working together)
**Plans:** 7 plans

Plans:
- [ ] 07-01-PLAN.md — LongRunningAction + ThresholdSpec + ThresholdEvaluator (pure dataclasses + evaluator)
- [ ] 07-02-PLAN.md — VisibilityProjector attention_state extension (Stage 5 suppress/boost)
- [ ] 07-03-PLAN.md — MechanicContext.begin_long_action() helper (mechanic-facing API)
- [ ] 07-04-PLAN.md — Engine tick hook + synthetic action routing + tick summary + runner integration
- [ ] 07-05-PLAN.md — Sleep seed mechanic (bounded, noise/health thresholds)
- [ ] 07-06-PLAN.md — Autopilot-travel seed mechanic + per-tick advance passive (bounded, hazard thresholds)
- [ ] 07-07-PLAN.md — Drunk seed mechanic + sober_up passive (indefinite, sobriety threshold)

## Progress

**Execution Order:**
Phases execute in numeric order: 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Universe Infrastructure | 0/2 | Planning complete | - |
| 1. Graph Foundation | 0/3 | Planning complete | - |
| 2. Mechanic Framework | 0/3 | Planning complete | - |
| 3. Design Validation | 0/3 | Not started | - |
| 4. Mechanic Authoring & Validation Infrastructure | 12/12 | Complete | 2026-04-13 |
| 5. Simulation Engine | 9/9 | Complete   | 2026-04-13 |
| 6. Resident Agent & End-to-End Loop | 7/7 | Complete   | 2026-04-13 |
| 7. Attention & Consciousness | 0/7 | Planning complete | - |
