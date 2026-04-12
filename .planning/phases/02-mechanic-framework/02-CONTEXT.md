# Phase 2: Mechanic Framework - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a stable mechanic protocol with DSL primitives, hand-written seed mechanics that prove the API works (including involuntary chain execution), mechanic versioning via git, a queryable registry, and CLI tooling for graph inspection and mechanic execution. All mechanics are git-versioned folders inside universe instances.

</domain>

<decisions>
## Implementation Decisions

### Mechanic Protocol (MECH-01)
- **D-01:** Mechanic base class with `check(ctx) -> CheckResult` and `apply(ctx) -> list[Mutation]`. CheckResult contains `passed: bool` and `reasons: list[str]` (reasons may be empty for simple mechanics).
- **D-02:** apply() returns `list[Mutation]` only. No observation hints — the engine synthesizes observations from mutations + graph state in Phase 5.
- **D-03:** Every mechanic has a unique `id: str` and `description: str` as class-level attributes. These are required for the execution trace and registry.
- **D-04:** Read-only mechanics (like Observation) use the same check/apply protocol with apply() returning an empty list. No separate query mechanic type.

### DSL Primitives (MECH-02)
- **D-05:** Context object pattern — `MechanicContext` wraps the graph and provides DSL methods: `query_node()`, `query_neighbors()`, `mutate()`, `add_node()`, `remove_node()`, `add_edge()`, `remove_edge()`. Mechanics never access KnowledgeGraph directly.
- **D-06:** The context also carries `actor` (who triggered the action) and `target` (what the action is directed at) as attributes, set by the engine before invocation.

### Voluntary vs Involuntary Mechanics & Chain Execution
- **D-07:** Mechanics have a `voluntary: bool` flag (default True). Voluntary mechanics fire from agent actions only. Involuntary mechanics fire reactively when graph mutations match their declared watchers.
- **D-08:** Involuntary mechanics declare matchers via a `watches()` method returning declarative matcher objects. Matchers are framework primitives — think event listeners based on property changes, edge additions, spatial proximity, or JSONPath-like selectors on graph state. NOT brute-force polling of all involuntary mechanics.
- **D-09:** Full chain execution engine included in Phase 2. After any apply() produces mutations, the engine evaluates involuntary mechanic matchers against those mutations. Matching mechanics get check()/apply() called, which may trigger further chains. Configurable max depth (default 10), cycle detection, and an execution trace tree.
- **D-10:** The execution trace is a tree structure recording which mechanic triggered which, with mutation details at each node. The engine (Phase 5) uses this trace + graph state to synthesize observations. The trace should be inspectable via the registry/CLI.

### Seed Mechanics (TEST-01)
- **D-11:** Three seed mechanics: Movement (voluntary — agent moves between connected locations), Observation (voluntary, read-only — gathers visible entities/properties), Environmental Reaction (involuntary — e.g., fire spreads to adjacent flammable entities when temperature changes).
- **D-12:** The environmental reaction mechanic validates the chain execution system end-to-end. It declares matchers (watches temperature changes), checks flammability of neighbors, and applies mutations that may trigger further chains.

### Versioning (MECH-05)
- **D-13:** Git commit = version. No semver in meta.yaml or code. Every commit that changes a mechanic folder is a version. The registry queries git log for mechanic history. Simple, no manual version bumping.

### Registry (MECH-06)
- **D-14:** Lightweight registry indexing mechanic folders within a universe. Supports list, inspect, query by id/tags, and git-based version history retrieval. The registry is an in-memory index built by scanning mechanic folders, not a database.

### Mechanic Folder Structure (MECH-05)
- **D-15:** Each mechanic is a folder: `mechanic.py` (the Mechanic subclass), `tests/` (unit tests), `meta.yaml` (metadata for registry/human consumption).

### meta.yaml Content
- **D-16:** Claude's Discretion. Include what the registry and downstream agents actually need — at minimum id, description, voluntary flag, tags. Keep it lightweight.

### CLI Tooling (AUTO-03)
- **D-17:** `list-mechanics <universe>` — List all mechanics with id, description, voluntary flag, last modified.
- **D-18:** `run-mechanic <universe> <mechanic-id> --actor <id> --target <id>` — Execute a specific mechanic against a universe's graph. For testing seed mechanics without the full simulation engine.
- **D-19:** `query-graph <universe>` — Query-based graph inspection with filters: `--type agent/entity`, `--has-property X`, `--near <node-id>`, `--limit N`, `--stats`. Returns matching nodes with properties. Supports summary stats mode for large graphs.
- **D-20:** No `inspect-mechanic` command — file IO and git commands suffice for reading mechanic source and history.

### Claude's Discretion
- D-16: meta.yaml content and depth
- Mechanic folder location strategy (built-in seed mechanics bundled in package vs universe-only)
- Matcher primitive API design (what declarative matcher types to support)
- Execution trace data structure details
- query-graph output format and filter syntax

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Design
- `docs/design/architecture.md` — System component diagrams, core simulation loop, KnowledgeGraph API shape
- `.planning/research/ARCHITECTURE.md` — Architecture research and design considerations

### Requirements
- `.planning/REQUIREMENTS.md` §Mechanic Framework — MECH-01 (protocol), MECH-02 (DSL primitives), MECH-05 (versioned folders), MECH-06 (registry)
- `.planning/REQUIREMENTS.md` §Testing — TEST-01 (unit tests for preconditions/side effects)
- `.planning/REQUIREMENTS.md` §Agent Autonomy — AUTO-03 (CLI scripts)

### Stack & Technology
- `.planning/research/STACK.md` — Full stack tables, model selection strategy

### Prior Phase Context
- `.planning/phases/00-universe-infrastructure/00-CONTEXT.md` — Universe structure (src-layout, XDG paths, mechanics/ folder in universe)
- `.planning/phases/01-graph-foundation/01-CONTEXT.md` — Graph API decisions (two node types, claim_id, JSON-serializable properties, mutation-mediated access)

### Existing Code (Phase 2 builds on)
- `src/token_world/graph/knowledge_graph.py` — KnowledgeGraph class with Query API (query, has_node, has_edge, neighbors, nodes) and Mutation API (add_node, add_edge, set, remove_node, remove_edge)
- `src/token_world/graph/models.py` — Mutation and SnapshotInfo dataclasses, ALLOWED_PROPERTY_TYPES
- `src/token_world/graph/__init__.py` — Public API exports
- `src/token_world/cli.py` — Existing Click CLI (create, list, delete commands)
- `src/token_world/universe/manager.py` — UniverseManager with create/load/list/delete

### Project Decisions
- `.planning/PROJECT.md` §Key Decisions — Mechanics as git-versioned folders, hybrid SDK architecture, Opus for mechanic generation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `KnowledgeGraph` class — The mechanic context wraps this; all DSL primitives delegate to its Query/Mutation API
- `Mutation` dataclass — apply() returns these directly; no new return type needed
- `claim_id()` — Seed mechanics creating new nodes use this for readable IDs
- `EventStore` / `GraphEvent` — Event infrastructure for audit trail; chain execution can log events per step
- Click CLI at `cli.py` — New commands (list-mechanics, run-mechanic, query-graph) extend this group
- `GraphBuilder` in `tests/test_graph/conftest.py` — Reuse for seed mechanic test setup

### Established Patterns
- Raw sqlite3 for persistence (no ORM)
- All graph mutations through KnowledgeGraph API (mechanic context enforces this)
- JSON-serializable property values only (ALLOWED_PROPERTY_TYPES)
- Two node types: agent and entity
- src-layout: new mechanic module at `src/token_world/mechanic/`
- Tests mirror src: `tests/test_mechanic/`

### Integration Points
- Mechanic module at `src/token_world/mechanic/` — protocol, context, registry, chain engine
- Seed mechanics inside universe `mechanics/` folders — need a bundling strategy (package data or copied on universe creation)
- CLI commands extend existing Click group in `cli.py`
- MechanicContext wraps KnowledgeGraph — does not subclass or modify it
- Chain execution trace feeds into Phase 5 (Simulation Engine) for observation synthesis

</code_context>

<specifics>
## Specific Ideas

- The matcher/listener pattern for involuntary mechanics is key to scalability — rather than polling every mechanic after every mutation, matchers declaratively specify what mutations they care about. Think CSS selectors or JSONPath but for graph mutations.
- The execution trace tree (which mechanic triggered which, with mutations at each node) is essential for the engine to formulate good observations. A single agent action might trigger 4 mechanics that each trigger 2 more — the engine needs to see this graph at a high level with tools to drill into details.
- The voluntary/involuntary distinction is the foundation of the "composition over specialization" philosophy — one mechanism (interruption thresholds in Phase 7) will reuse the same involuntary mechanic infrastructure for sleep, daydreaming, autopilot travel, etc.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. The chain execution requirement was correctly identified as part of the mechanic framework, not scope creep.

</deferred>

---

*Phase: 02-mechanic-framework*
*Context gathered: 2026-04-11*
