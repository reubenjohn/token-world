# Phase 3: Design Validation - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a use case library covering diverse interaction scenarios (~35 cases with both narrative vignettes and structured action-observation pairs), run gap analysis (per-use-case + per-architecture-layer), add optional spatial (R-tree) and temporal indexes to the graph, and provide filtered Mermaid graph visualization via CLI. Knowledge graphs can contain thousands of nodes — all visualization and indexing must account for scale.

</domain>

<decisions>
## Implementation Decisions

### Use Case Design (DVAL-01)
- **D-01:** Use cases have both layers: narrative vignette for human understanding + structured action-observation pairs for machine testing. The structured pairs become regression specs in Phase 6 (DVAL-03).
- **D-02:** ~35 total use cases across categories (spatial, social, resource, environmental, edge-case). Claude decides distribution per category based on complexity — some categories may need more than others.
- **D-03:** Use cases go beyond existing seed mechanics. Scenarios should cover the full range of interactions (crafting, trading, combat, social, environmental cascades, etc.) even if no mechanic exists yet. This is the purpose — gap analysis finds what's missing.
- **D-04:** Implementation should use parallel agent waves — dedicated agents per category or per case, launched in waves. The planner should design for this parallelism.

### Gap Analysis Process (DVAL-02)
- **D-05:** Both perspectives: per-use-case gap identification first (each use case notes what mechanics/framework capabilities it needs), then aggregate and re-examine per architecture layer (graph API, mechanic protocol, engine pipeline).
- **D-06:** Three-way disposition for gaps: Address now (add to this or next phase), Defer (backlog for later milestone), Out of scope (explicitly won't do).
- **D-07:** Inline + summary format: each use case file notes its own gaps inline, plus a standalone GAP-ANALYSIS.md summary report that aggregates all gaps cross-referenced to use cases.

### Optional Indexes (GRAPH-06, GRAPH-07)
- **D-08:** Claude's Discretion on spatial index integration. Options include DSL method on MechanicContext (ctx.query_nearby) with lazy-loaded R-tree, or separate index object. Pick what fits the existing MechanicContext DSL best while keeping mechanics that don't need spatial queries cost-free.
- **D-09:** Claude's Discretion on temporal index design. Options include event-time queries on the existing EventStore/GraphEvent infrastructure (query_history, query_changes) or time-series property values. Pick what works best with existing graph event infrastructure.

### Graph Visualization (AUTO-04)
- **D-10:** Two visualization modes: local neighborhood inspection (debugging — "show me what's near X") and high-level summary views (orientation — agents, major locations, connectivity patterns).
- **D-11:** CLI command invocation: `viz-graph <universe> --node <id> --depth N --type <filter>`. Outputs Mermaid markdown to stdout or file. Consistent with existing CLI pattern.
- **D-12:** Claude's Discretion on filtering strategy. Ego-graph (center on node, expand N hops — NetworkX has ego_graph() built in) is the natural fit for local inspection. May combine with query-based filtering for property/type constraints.
- **D-13:** Claude's Discretion on node detail level in Mermaid diagrams. Balance readability with usefulness for debugging mechanics against large graphs.
- **D-14:** Graphs can contain thousands of nodes. Whole-graph rendering is NOT a goal. All visualization must be filtered. Document this constraint prominently.

### Claude's Discretion
- D-08: Spatial index integration pattern
- D-09: Temporal index design
- D-12: Filtering strategy (ego-graph, query-based, or hybrid)
- D-13: Node detail level in Mermaid diagrams
- Use case distribution across categories

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Design
- `docs/design/architecture.md` — System component diagrams, core simulation loop, KnowledgeGraph API shape
- `.planning/research/ARCHITECTURE.md` — Architecture research and design considerations

### Requirements
- `.planning/REQUIREMENTS.md` §Design Validation — DVAL-01 (use case library), DVAL-02 (gap analysis)
- `.planning/REQUIREMENTS.md` §Knowledge Graph — GRAPH-06 (R-tree spatial index), GRAPH-07 (temporal index)
- `.planning/REQUIREMENTS.md` §Agent Autonomy — AUTO-04 (Mermaid graph visualization)

### Stack & Technology
- `.planning/research/STACK.md` — Full stack tables, technology decisions

### Prior Phase Context
- `.planning/phases/01-graph-foundation/01-CONTEXT.md` — Graph API decisions (two node types, claim_id, JSON-serializable properties, mutation-mediated access, EventStore/GraphEvent infrastructure)
- `.planning/phases/02-mechanic-framework/02-CONTEXT.md` — Mechanic protocol (check/apply, MechanicContext DSL, voluntary/involuntary, chain execution, seed mechanics, registry, CLI tooling)

### Existing Code (Phase 3 builds on)
- `src/token_world/graph/knowledge_graph.py` — KnowledgeGraph class with Query/Mutation API; spatial/temporal indexes integrate here
- `src/token_world/graph/events.py` — EventStore and GraphEvent; temporal index builds on this
- `src/token_world/graph/models.py` — Mutation, SnapshotInfo, ALLOWED_PROPERTY_TYPES
- `src/token_world/cli.py` — Existing Click CLI; viz-graph command extends this

### Project Decisions
- `.planning/PROJECT.md` §Key Decisions — Composition over specialization, graph is ground truth

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `KnowledgeGraph` class — spatial/temporal index primitives integrate as optional extensions
- `EventStore` / `GraphEvent` — temporal index queries can leverage existing event infrastructure (events already record tick_id, event type, target, old/new values)
- `NetworkX ego_graph()` — built-in function for ego-graph extraction; natural fit for filtered visualization
- Click CLI at `cli.py` — viz-graph command extends the existing command group
- `GraphBuilder` in `tests/test_graph/conftest.py` — reuse for constructing test graphs for use cases

### Established Patterns
- All graph access through KnowledgeGraph API (mechanic context enforces this)
- MechanicContext wraps graph with DSL methods — new index queries should follow this pattern
- Raw sqlite3 for persistence (no ORM)
- src-layout: new modules at `src/token_world/graph/` or `src/token_world/viz/`
- CLI commands as Click subcommands

### Integration Points
- Spatial/temporal indexes extend KnowledgeGraph or MechanicContext (Phase 2 established the DSL pattern)
- viz-graph CLI command outputs Mermaid markdown; mcp-mermaid server can render it
- Use case action-observation pairs become Phase 6 regression tests (DVAL-03)
- Gap analysis report informs Phase 4 (LLM Mechanic Generation) and Phase 5 (Simulation Engine) planning

### Scale Consideration
- Knowledge graphs can contain thousands of nodes — all queries, indexes, and visualizations must be designed for this scale from the start

</code_context>

<specifics>
## Specific Ideas

- Use case authoring should be parallelized via agent waves — dedicated agents per category or per individual case, launched in waves. This is a planning/execution concern for the planner to design.
- The gap analysis is the core value of this phase — use cases exist primarily to find gaps before building the simulation engine. The use case library is the input; the gap analysis is the output that shapes Phases 4-5.
- Mermaid without filtering is useless at scale. The CLI must enforce filtering (require --node or similar). No "render everything" mode.
- Temporal index should leverage existing EventStore infrastructure rather than inventing a new storage model.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-design-validation*
*Context gathered: 2026-04-12*
