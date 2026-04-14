# Project Research Summary

**Project:** Token World
**Domain:** LLM-powered procedural universe simulation
**Researched:** 2026-04-11
**Archived:** 2026-04-15 — see "Stale claims rectified at archival" note below before relying on any specific recommendation.
**Confidence:** MEDIUM-HIGH

> **Stale claims rectified at archival (Session 4, 2026-04-15):**
> - **Mechanic generator model:** Opus (via Agent SDK), NOT Sonnet. Token World v1.0 ships with Opus authoring mechanics through the Phase 04.1 Operator Agent Harness ($1.15/23 turns observed in production). References below to "Sonnet for mechanic code generation" are wrong; CLAUDE.md / `src/token_world/operator/` are authoritative.
> - **Mechanic Registry:** flat module-based registry (`mechanics/<id>.py` auto-scan), NOT folder-per-mechanic, NOT concept-indexed. The Phase 2 D-15 folder-per-mechanic decision was superseded by Phase 4 (single-file convention; see `04-llm-mechanic-generation/04-01-PLAN.md`).
> - **Sandboxing:** RestrictedPython is NOT shipped in v1. The validation pipeline (6-stage gate) replaces it; sandboxing was deferred to v2.
> - **Phase numbering note:** the original 6-phase plan in §"Implications for Roadmap" was reorganised during planning; the actual v1.0 ship list is Phases 0..7, plus inserted decimal phases 04.1 + 07.1. See `.planning/milestones/v1.0-ROADMAP.md`.

## Executive Summary

Token World is a novel class of project: a self-extending simulation where LLM-generated Python code (mechanics) becomes the rule system of the world, and a knowledge graph (NetworkX + SQLite) is the world's ground truth. The pattern most closely resembles an event-sourced game engine where the rule set is not authored up front but synthesized on demand. Research confirms this is a viable architecture with well-understood component boundaries — the core loop (agent action -> classify -> mechanic lookup/generate -> execute -> observation) is simple enough to implement without an agent framework, and the persistence model (in-memory graph + event log + snapshots) is a known-good pattern for this scale.

The recommended approach is a layered build: foundation (graph + persistence) first, then the mechanic framework API, then LLM generation wired on top, and finally the resident agent as the consumer. This order respects the hard dependency chain identified in research — nothing above the graph can be built without the graph. The stack is deliberately minimal: Python 3.12, NetworkX, SQLite, Anthropic SDK, Pydantic, RestrictedPython. No web server, no agent framework, no graph database. Every heavier alternative was evaluated and rejected because the graph will be small (hundreds to low thousands of nodes) for the foreseeable future and the simulation loop is single-agent and synchronous.

The dominant risks are logical, not technical. Mechanic incoherence (generated rules that contradict each other), ungrounded observations (the engine describing a world that does not match graph state), and generated code execution escapes are the three critical failure modes. All three are mitigable with disciplined design choices established from Phase 1: the Mutation pattern (mechanics never touch the graph directly), the GraphMutator event log (every change is auditable and reversible), and a controlled exec namespace (RestrictedPython plus allowlisted builtins only). The time to establish these constraints is before any mechanics are generated, not after.

## Key Findings

### Recommended Stack

The stack is Python-centric and avoids server dependencies. NetworkX provides in-memory graph operations with a schema-less dict-of-dicts model that maps naturally to the emergent property requirement. SQLite provides durable persistence with zero configuration via a custom ~200-line adapter — not an ORM, not a graph database, not an event-sourcing library. The Anthropic SDK is used directly (not via LangChain or LangGraph) to maintain full control over prompt construction, model selection, and token budgets. RestrictedPython provides compile-time AST restriction for generated mechanic code.

**Core technologies:**
- Python 3.12+: engine language — rich AI/ML ecosystem, 3.12 performance improvements
- NetworkX 3.6.1: in-memory knowledge graph — schema-less dict attributes, full algorithm library, JSON serialization built in
- SQLite (stdlib): persistence — zero-config, JSON1 extension, WAL mode, event log and snapshot pattern
- Anthropic SDK 0.80+: LLM access — structured outputs GA, full prompt control, tool use
- Pydantic 2.12+: data validation — structured output schemas, native Anthropic SDK integration
- RestrictedPython 8.2: mechanic sandboxing — AST-level restriction, blocks dangerous ops at compile time

**Model selection strategy (v1.0 actual, post-archival rectification):** Haiku 4.5 for classification, mechanic matching, and resident-agent personality. Sonnet 4.6 for observation synthesis (D-15 hard grounding). **Opus 4.6 (via Claude Agent SDK) for mechanic code generation** — superseded the original Sonnet recommendation per Phase 04.1 D-02. Observed cost $1.15/23 turns for one mechanic at the operator layer; per-tick simulation cost remains $0.01-0.05 with Haiku-heavy routing.

**Do not use:** LangChain, LangGraph, CrewAI, FastAPI, SQLAlchemy, MongoDB, Neo4j, pickle, Celery. Defer Claude Agent SDK to v2+ (multi-agent).

### Expected Features

**Must have (table stakes) — v1 cannot function without these:**
- Knowledge graph with arbitrary properties — core data model; emergent concepts require schema-less graph
- Mechanic framework (preconditions + side effects) — API surface that generated code targets
- LLM mechanic generation — the core innovation; without this it is a static rule engine
- Simulation engine (action -> mechanic -> observation) — main loop that wires everything together
- Resident agent with personality — the entity that generates actions
- Graph state persistence — survives restarts; core requirement
- Mechanic persistence and versioning — full history of all generated mechanics
- Graph state snapshots + event log — enable rollback and replay
- Simulation history log — track what happened for debugging

**Should have (differentiators) — high value, deliver after core loop is proven:**
- Emergent concept creation — properties like temperature and hunger appear only when mechanics create them
- Grounded observations — all engine responses derive from graph state, never hallucinated
- Natural language action parsing — maps free text to structured mechanic triggers

**Defer to v1.1+:**
- Mechanic coherence checking — requires an existing body of mechanics; complex to implement correctly
- Time-travel debugging UI — event log data will exist; tooling can come later
- Multi-agent simulation — requires solving agent-agent interaction; v2 concern
- Web UI or visual output — CLI-first; prove the loop works before adding rendering

### Architecture Approach

The architecture is a clean pipeline of specialized components with single-directional data flow: the Resident Agent produces text actions, the Simulation Engine interprets them, the Mechanic Registry and Mechanic Generator supply executable rules, the Mechanic Framework defines the API those rules target, the Knowledge Graph holds world state, and the Persistence Layer makes all of it durable. Two structural decisions are non-negotiable: (1) mechanics are pure functions that return Mutations rather than modifying the graph directly, and (2) every graph change passes through a central GraphMutator that logs events before applying them. These two decisions unlock rollback, auditing, testing, and time-travel debugging without any additional infrastructure.

**Major components:**
1. Resident Agent — Haiku-powered with personality system prompt; produces action text; consumes observation text
2. Simulation Engine — pipeline of focused LLM calls (classify -> select -> generate? -> execute -> observe); the orchestrator
3. Mechanic Registry — indexed by trigger concept; dict keyed by concept with lists of mechanics per concept
4. Mechanic Generator — **Opus**-powered code generation via Claude Agent SDK (Phase 04.1 Operator Harness), NOT Sonnet; produces Mechanic-protocol-compliant Python through normal SDLC + 6-stage validation pipeline
5. Mechanic Framework — pure Python Protocol defining `check(graph, context) -> bool` and `apply(graph, context) -> list[Mutation]`
6. Knowledge Graph — NetworkX DiGraph; nodes and edges with arbitrary dict attributes; entirely in-memory at runtime
7. Persistence Layer — custom SQLite adapter; graph_snapshots, graph_events, mechanics, mechanic_versions, simulation_log tables

### Critical Pitfalls

1. **Mechanic Incoherence Spiral** — Generated mechanics contradict each other; world becomes logically inconsistent. Prevent by including all existing mechanics touching the same concepts in the generation prompt; start with manually written seed mechanics to establish ground truth.

2. **Ungrounded Observation Drift** — Engine generates observations that do not match graph state; agent acts on hallucinated information. Prevent by always including current graph node state in the observation prompt; never ask the LLM to describe the world without providing the graph facts explicitly.

3. **Generated Code Execution Escapes** — A mechanic accesses filesystem, network, or Python internals through RestrictedPython gaps (CVE-2025-22153 exists for try/except* patterns). Prevent by controlled exec namespace (no `os`, `sys`, `subprocess`, `socket`, `importlib`); AST validation before execution; subprocess isolation as fallback; pin RestrictedPython version.

4. **Graph State Corruption Without Recovery** — Malformed mutations propagate before detection. Prevent by validating mutations before applying (target nodes exist, types match); define and check graph invariants after every mutation batch; event log and snapshots provide rollback to last known-good state.

5. **Mechanic Framework API Instability** — API changes break all previously generated mechanics. Prevent by designing and validating the API with hand-written test mechanics before any LLM generation; keep the API surface small (query_node, query_neighbors, mutate as the core three operations).

## Implications for Roadmap

Based on the dependency chain from FEATURES.md and the structural constraints from ARCHITECTURE.md, the project naturally divides into 6 phases. The ordering is non-negotiable for Phases 1-4 — each layer depends on the one below it. Phases 5 and 6 can overlap slightly once Phase 4 is validated.

### Phase 1: Graph Foundation
**Rationale:** Everything else depends on the knowledge graph and persistence layer. Cannot build the mechanic framework without a stable graph API. Cannot test anything without persistence. This is the project's bedrock and must include the event log from the start — retrofitting it later breaks the audit trail.
**Delivers:** NetworkX DiGraph wrapper, GraphMutator with event logging, SQLite persistence adapter (snapshots + event log + mechanics tables), graph invariant checking, seed world bootstrap (1 location, 3-5 objects, basic properties).
**Addresses:** "Knowledge graph with arbitrary properties", "Graph state persistence", "Graph state snapshots"
**Avoids:** Graph state corruption without recovery (Pitfall 4 — invariant checks from day one), over-engineering schema (zero schema; let mechanics define properties), pickle persistence (use JSON serialization via NetworkX json_graph).

### Phase 2: Mechanic Framework
**Rationale:** Defines the API surface that all generated mechanic code must target. Must be stable before any LLM generation is attempted. Manual mechanics written here serve as generation examples and as regression tests for the API.
**Delivers:** Mechanic Protocol (check + apply), Mutation dataclass, GraphMutator integration, 3-5 hand-written seed mechanics (movement, observation, basic interaction), mechanic execution pipeline (run check -> apply mutations -> log), mechanics table and versioning in SQLite.
**Addresses:** "Mechanic framework (preconditions + side effects)", "Mechanic persistence and versioning"
**Avoids:** API instability (Pitfall 6 — iterate with manual mechanics before LLM touches it), API bloat (start with 3 primitives: query_node, query_neighbors, mutate).

### Phase 3: LLM Mechanic Generation
**Rationale:** With a stable framework API and hand-written examples available, mechanic generation has a well-defined target. This is the highest-complexity phase — prompt engineering, structured output schemas, sandboxing, and validation all converge here.
**Delivers (per v1.0 actual):** Mechanic authoring via Claude Agent SDK with **Opus** (not Sonnet), generation prompt with framework docs and examples, **6-stage validation pipeline** (syntax -> AST -> import -> contract -> tests -> dry-execute) replacing the originally-planned RestrictedPython sandbox (deferred to v2), mechanic naming and collision detection via `claim_id()`.
**Addresses:** "LLM mechanic generation", "Emergent concept creation"
**Avoids:** Code execution escapes (Pitfall 3 — sandbox built before first generation), mechanic naming collisions (Pitfall 8), testing generated code without scenarios (Pitfall 12).

### Phase 4: Simulation Engine
**Rationale:** The simulation engine wires together all components built in Phases 1-3. It is the main loop: classify action, look up mechanic, generate if missing, execute, format observation. At the end of this phase the core loop runs end-to-end without a live agent.
**Delivers:** Action classifier (Haiku + structured output), Mechanic Registry (concept-indexed), engine pipeline (classify -> select -> generate? -> execute -> observe), observation formatter (graph-grounded), simulation history log, CLI harness for manual action input.
**Addresses:** "Simulation engine (action -> mechanic -> observation)", "Simulation history log", "Natural language action parsing", "Grounded observations"
**Avoids:** Monolithic prompts (Architecture anti-pattern 4 — separate LLM call per task), ungrounded observation drift (Pitfall 2 — observation prompt always includes graph context), global mechanic namespace (Architecture anti-pattern 3 — module-based registry per Phase 4 D-15 supersession), token cost explosion (Pitfall 5 — Haiku for classify, Sonnet for observe, Opus for authoring at the operator layer only).

### Phase 5: Resident Agent
**Rationale:** The agent is the consumer of the simulation engine. It is the last core component because it requires a working engine to interact with. Agent complexity is low relative to the engine — it is a personality system prompt plus memory context plus an action generation loop.
**Delivers:** Resident agent component (Haiku + personality system prompt), agent memory management (recent N turns + summarized long-term memory in SQLite), agent-engine interaction loop, configurable agent personas, seed world interaction to validate the end-to-end experience.
**Addresses:** "Resident agent with personality"
**Avoids:** Agent memory explosion (Pitfall 7 — memory management strategy from the start), flat personality (invest in prompt with specific quirks, speech patterns, and goals; test multiple personas), empty world bootstrap problem (Pitfall 11 — seed world from Phase 1).

### Phase 6: Observability and Hardening
**Rationale:** Once the end-to-end loop runs, add the diagnostic tools that make it debuggable and resilient. The event log data is already present from Phase 1; this phase adds tooling on top. Mechanic coherence checking becomes valuable once a meaningful body of mechanics exists.
**Delivers:** State inspection CLI commands (graph dump, mechanic list, simulation history), snapshot-based replay (load snapshot, replay events to step N), mechanic coherence checker (LLM-based contradiction detection), grounding score metric, cost-per-step monitoring and alerting.
**Addresses:** "Mechanic coherence checking", time-travel debugging (data model exists from Phase 1; tooling added here)
**Avoids:** Building replay tooling before the data exists (data is present by Phase 6), over-engineering persistence into CQRS or projections (Pitfall 9).

### Phase Ordering Rationale

- Phases 1-4 form a hard dependency chain: graph -> framework -> generation -> engine. Reordering any of these creates a circular dependency (cannot test generation without a framework; cannot test the engine without generation working).
- Phase 5 (Agent) follows Phase 4 (Engine) because the agent's only interface is the engine. It can be developed in parallel with late Phase 4 once the engine API is stable.
- Phase 6 (Observability) is last because its value compounds as the mechanic set grows. Building it too early means there is little state to observe and the coherence checker has no mechanics to check.
- The seed world (Phase 1) and seed mechanics (Phase 2) establish ground truth before any LLM generation occurs. This is the primary mitigation for the Mechanic Incoherence Spiral and directly de-risks Phase 3.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Mechanic Generation):** RestrictedPython CVE-2025-22153 needs review — confirm whether the controlled namespace workaround is sufficient or whether subprocess isolation should be the default. Prompt engineering for mechanic generation is empirical and will require iteration before quality is acceptable.
- **Phase 4 (Simulation Engine):** Observation grounding prompt design is non-trivial. Action classification schema granularity (right set of verbs and contexts) cannot be determined in advance; plan for 1-2 iteration cycles.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Graph Foundation):** NetworkX + SQLite patterns are well-documented with official sources. Custom persistence adapter is straightforward Python.
- **Phase 2 (Mechanic Framework):** Pure Python Protocol plus dataclass pattern. No novel technology.
- **Phase 5 (Resident Agent):** Standard Anthropic SDK usage with Haiku model. Memory summarization is a well-known pattern.
- **Phase 6 (Observability):** CLI tooling over existing data structures. No novel technology.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core libraries verified against official docs and PyPI. Version numbers confirmed. Alternatives systematically evaluated with clear rationale for rejection. |
| Features | HIGH | Feature set derived directly from project goals and dependency analysis. Anti-features are well-reasoned with specific v1.1+ deferral rationale. |
| Architecture | HIGH | Component boundaries are clean and well-established (Protocol, Mutation, event sourcing). No novel architectural bets. Cost estimates are approximate but directionally correct. |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls (incoherence, drift, sandbox escapes, corruption) are well-grounded in LLM agent literature. RestrictedPython CVE is a real and documented concern. Coherence checking mitigation is best-effort and needs empirical validation during Phase 3. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **RestrictedPython CVE-2025-22153 severity and workaround:** The CVE exists for try/except* patterns. Need to confirm whether the controlled namespace approach is a sufficient workaround, or whether subprocess isolation should be the default for all mechanic execution in Phase 3.
- **Mechanic generation prompt quality:** Research recommends including 3-4 example mechanics and all related existing mechanics in the generation prompt, but the right prompt structure is empirical. Expect 1-2 iteration cycles in Phase 3 before generation quality is acceptable.
- **Action classification schema granularity:** The verb/subject/object/context structure is recommended, but the right vocabulary for a novel simulation world cannot be determined in advance. Plan for iteration in Phase 4.
- **Observation grounding implementation:** A two-step approach (extract facts from graph, then generate prose from facts) is recommended but not yet prototyped. The grounding check (verify claims against graph after generation) adds latency and cost. May need to simplify to prompt-only grounding in v1 and add the check in Phase 6.
- **Mechanic coherence at scale:** The coherence checker is deferred to Phase 6, but the incoherence problem may surface during Phase 3 validation. Be prepared to pull forward Phase 6 coherence work if mechanics start contradicting each other before the loop is complete.
- **Claude model IDs at implementation time:** Model IDs referenced in research (e.g., `claude-haiku-4-5-20250315`, `claude-sonnet-4-5-20250514`) reflect current naming conventions but should be verified against the Anthropic API at implementation time.

## Sources

### Primary (HIGH confidence)
- [NetworkX 3.6.1 documentation](https://networkx.org/documentation/stable/) — graph operations, attributes, JSON serialization
- [NetworkX JSON serialization](https://networkx.org/documentation/stable/reference/readwrite/json_graph.html) — persistence serialization format
- [Anthropic Python SDK (PyPI)](https://pypi.org/project/anthropic/) — SDK version, structured outputs GA status
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — Pydantic integration, schema compliance guarantees
- [Anthropic tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use) — tool loop implementation
- [RestrictedPython 8.2 documentation](https://restrictedpython.readthedocs.io/) — AST restriction, Python version support, CVE-2025-22153
- [Pydantic 2.12+ documentation](https://docs.pydantic.dev/latest/) — validation, Anthropic integration
- [SQLite JSON1 extension](https://sqlite.org/json1.html) — JSON column querying
- [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) — rationale for deferring to v2+

### Secondary (MEDIUM confidence)
- [AI Agent Frameworks Compared 2026](https://letsdatascience.com/blog/ai-agent-frameworks-compared) — rationale for raw SDK over LangGraph and CrewAI
- [Code Sandboxes for LLMs](https://amirmalik.net/2025/03/07/code-sandboxes-for-llm-ai-agents) — sandbox comparison, RestrictedPython vs Docker tradeoffs
- [Setting up secure Python sandbox for LLM agents](https://dida.do/blog/setting-up-a-secure-python-sandbox-for-llm-agents) — controlled namespace design
- [Event sourcing patterns](https://eventsourcing.readthedocs.io/en/stable/topics/introduction.html) — snapshot + event log pattern reference
- [NetworkX persistence challenges](https://memgraph.com/blog/data-persistency-large-scale-data-analytics-and-visualizations-biggest-networkx-challenges) — scale limits and alternatives
- [Automated KG pipeline with LangGraph/NetworkX](https://kiadev.net/news/2025-05-15-automated-knowledge-graph-pipeline-langgraph-networkx) — LLM + knowledge graph integration patterns

### Tertiary (reviewed but rejected)
- [simple-graph-sqlite v2.1.0 (PyPI)](https://pypi.org/project/simple-graph-sqlite/) — last updated 2022; limited query capabilities; rejected in favor of NetworkX
- [eventsourcing v9.5.4 (PyPI)](https://pypi.org/project/eventsourcing/) — enterprise DDD framework; overkill for ~200 LOC custom solution; rejected

---
*Research completed: 2026-04-11*
*Ready for roadmap: yes*
