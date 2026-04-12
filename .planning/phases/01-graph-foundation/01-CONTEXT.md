# Phase 1: Graph Foundation - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a persistent, snapshot-capable knowledge graph that supports arbitrary emergent properties, can be rolled back to any previous state, and includes test infrastructure and project-level autonomy docs. The graph is the ground truth for all simulation state — if it's not in the graph, it doesn't exist.

</domain>

<decisions>
## Implementation Decisions

### Node Identity & Typing
- **D-01:** Framework knows exactly two fundamental node types: `agent` and `entity`. Everything else is emergent — the framework makes no assumptions about what kinds of entities exist. This maximizes mechanic flexibility.
- **D-02:** Node IDs are mechanic-driven via a `claim_id(name)` helper. The mechanic that creates a node proposes a human-readable ID. The graph deconflicts: `"wallet"` if available, `"wallet_a7"` if taken, `"wallet_a7z6"` if many collisions. IDs are readable for debugging but unique.
- **D-03:** No other framework-enforced properties or constraints on nodes. Mechanics add whatever properties they need. The framework is deliberately minimal to avoid constraining what mechanics can express.

### Property Value Flexibility
- **D-04:** Claude's Discretion. Choose whatever property value types best serve the emergent-property philosophy while keeping persistence reliable. Consider: primitives are safe and simple; nested structures enable richer concepts but complicate serialization. Balance flexibility with debuggability.

### Snapshot Semantics
- **D-05:** Every tick is identifiable by a tick ID. Snapshots are linked to tick identifiers — a snapshot records "graph state as of tick N."
- **D-06:** Snapshot names are derived from a summary of changes since the last snapshot, built from hierarchical tick summaries. E.g., a summary of batch-300-400 + batch-400-500 + tick-501 + tick-502 produces a human-readable snapshot name.
- **D-07:** Claude's Discretion for remaining snapshot details: storage format, retention policy, maximum count, and whether snapshots are SQLite-internal or git-integrated. Optimize for the rollback use case (operator wants to rewind to "before X happened").

### CLAUDE.md Update (AUTO-01)
- **D-08:** Claude's Discretion. The project-level CLAUDE.md should contain whatever is needed for an agent (human or AI) to understand and work on the project autonomously — architecture overview, critical constraints, validation protocols, script catalog. Scope and depth are Claude's call.

### Claude's Discretion
- D-04: Property value types — balance flexibility with persistence reliability
- D-07: Snapshot storage details — format, retention, git integration
- D-08: CLAUDE.md content and depth — whatever achieves agent autonomy

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Design
- `docs/design/architecture.md` — System component diagrams, core simulation loop, KnowledgeGraph class diagram with API shape (query, set, add_node, add_edge, snapshot, restore), Mutation model
- `.planning/research/ARCHITECTURE.md` — Architecture research and design considerations

### Requirements
- `.planning/REQUIREMENTS.md` §Knowledge Graph — GRAPH-01 (arbitrary properties), GRAPH-02 (emergent concepts), GRAPH-03 (SQLite persistence), GRAPH-04 (snapshot), GRAPH-05 (restore)
- `.planning/REQUIREMENTS.md` §Testing — TEST-03 (snapshot/restore round-trip), TEST-06 (convenience graph builders)
- `.planning/REQUIREMENTS.md` §Agent Autonomy — AUTO-01 (CLAUDE.md with architecture, constraints, validation, scripts)

### Stack & Technology
- `.planning/research/STACK.md` — Full stack tables, NetworkX + SQLite decisions, persistence architecture, model selection
- `CLAUDE.md` §Technology Stack — Python 3.12+, NetworkX (in-memory), SQLite (persistence)

### Prior Phase Context
- `.planning/phases/00-universe-infrastructure/00-CONTEXT.md` — Universe structure decisions (src-layout, XDG paths, empty graph at creation, SQLite via universe.db)

### Project Decisions
- `.planning/PROJECT.md` §Key Decisions — Schema-less graph, full persistence, mechanics as git-versioned folders, hierarchical tick summaries

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/token_world/models.py` — Pydantic model pattern (UniverseMetadata); extend for graph-related models
- `src/token_world/universe/manager.py` — SQLite usage pattern (raw sqlite3, no ORM); reuse for graph persistence
- `src/token_world/universe/paths.py` — XDG path resolution; universe data dir is where universe.db lives
- `tests/conftest.py` — Existing pytest configuration; extend with graph fixtures

### Established Patterns
- Raw sqlite3 for persistence (no SQLAlchemy ORM per project constraints)
- Pydantic for data models with validation
- Click for CLI
- src-layout package structure at `src/token_world/`
- Tests in `tests/` mirroring src structure

### Integration Points
- Graph module should live at `src/token_world/graph/` following the existing `universe/` subpackage pattern
- Graph persists to `universe.db` inside each universe folder (already created by UniverseManager)
- MCP tools (resume_tick, rollback) will call graph snapshot/restore in later phases
- Mechanic framework (Phase 2) will use the graph API as its primary interface

</code_context>

<specifics>
## Specific Ideas

- The `claim_id()` pattern is central: mechanics propose readable IDs, the graph guarantees uniqueness. This keeps the world debuggable (you see "wallet" not "a7f3b2c1") while preventing collisions.
- The "blank slate" philosophy from Phase 0 (D-07) continues: the graph starts empty, everything emerges from mechanics. The framework should not assume any properties exist on any node.
- Tick-linked snapshots with summary-derived names mean the operator can browse snapshots like a timeline of "what happened" rather than opaque timestamps.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-graph-foundation*
*Context gathered: 2026-04-11*
