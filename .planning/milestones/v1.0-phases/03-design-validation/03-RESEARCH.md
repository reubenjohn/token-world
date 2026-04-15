# Phase 3: Design Validation - Research

**Researched:** 2026-04-12
**Domain:** Use case library authoring, gap analysis, optional graph indexes (R-tree, temporal), filtered Mermaid visualization
**Confidence:** HIGH (patterns/libraries well-established; a few discretion items are pragmatic choices)

## Summary

Phase 3 is a design validation phase, not a feature phase. Its first-class output is the **gap analysis**, not code. The use case library and optional indexes exist to pressure-test the framework before Phase 4 (LLM generation) and Phase 5 (Simulation Engine) are built on top of it. Everything must be parseable by downstream LLM agents and regression tests (Phase 6, DVAL-03).

**Primary recommendation:**

1. Author use cases as **single-file YAML-frontmatter markdown** — narrative in the body, structured `scenario` / `actions` / `observations` / `gaps` in YAML frontmatter. One loader parses both halves. This avoids a markdown-plus-sidecar split that invariably drifts.
2. Use **5 parallel category waves** (spatial, social, resource, environmental, edge-case) each with 1 planning task + N authoring tasks + 1 per-category aggregation task. Cross-category gap synthesis happens in a final serial wave.
3. **Temporal queries as `EventStore` wrappers** — no new storage. The event log already has `tick_id`, `event_type`, `target_id`, `property_name`, `old_value_json`, `new_value_json` — everything needed for `query_history`, `query_changes`, `find_state_at_tick`. Add a dedicated `TemporalIndex` facade that queries over the live events + SQLite `graph_events` table.
4. **Spatial index as a lazy `MechanicContext.spatial` accessor** backed by Toblerity `rtree` 1.4.1. 2D bounding boxes only for v1. Positions live on nodes as `position: [x, y]` or `bbox: [minx, miny, maxx, maxy]`. Index is built on first access per-tick and invalidated by any mutation touching position. Mechanics that don't touch spatial data pay zero cost.
5. **Filtered Mermaid** via NetworkX `ego_graph()` as the default, with mandatory `--node` (single node anchor) or `--seed-query` (property/type filter that selects anchors). No "render all" mode. Hard cap at ~150 nodes in output — refuse to render beyond that, tell the user to tighten the filter.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Use Case Design (DVAL-01)**
- **D-01:** Use cases have both layers: narrative vignette for human understanding + structured action-observation pairs for machine testing. The structured pairs become regression specs in Phase 6 (DVAL-03).
- **D-02:** ~35 total use cases across categories (spatial, social, resource, environmental, edge-case). Claude decides distribution per category based on complexity — some categories may need more than others.
- **D-03:** Use cases go beyond existing seed mechanics. Scenarios should cover the full range of interactions (crafting, trading, combat, social, environmental cascades, etc.) even if no mechanic exists yet. This is the purpose — gap analysis finds what's missing.
- **D-04:** Implementation should use parallel agent waves — dedicated agents per category or per case, launched in waves. The planner should design for this parallelism.

**Gap Analysis Process (DVAL-02)**
- **D-05:** Both perspectives: per-use-case gap identification first (each use case notes what mechanics/framework capabilities it needs), then aggregate and re-examine per architecture layer (graph API, mechanic protocol, engine pipeline).
- **D-06:** Three-way disposition for gaps: Address now (add to this or next phase), Defer (backlog for later milestone), Out of scope (explicitly won't do).
- **D-07:** Inline + summary format: each use case file notes its own gaps inline, plus a standalone GAP-ANALYSIS.md summary report that aggregates all gaps cross-referenced to use cases.

**Graph Visualization (AUTO-04)**
- **D-10:** Two visualization modes: local neighborhood inspection (debugging — "show me what's near X") and high-level summary views (orientation — agents, major locations, connectivity patterns).
- **D-11:** CLI command invocation: `viz-graph <universe> --node <id> --depth N --type <filter>`. Outputs Mermaid markdown to stdout or file. Consistent with existing CLI pattern.
- **D-14:** Graphs can contain thousands of nodes. Whole-graph rendering is NOT a goal. All visualization must be filtered. Document this constraint prominently.

### Claude's Discretion

- **D-08:** Spatial index integration pattern (addressed in this research — recommend lazy `ctx.spatial` accessor)
- **D-09:** Temporal index design (addressed in this research — recommend EventStore wrapper facade, no new storage)
- **D-12:** Filtering strategy for Mermaid (addressed — recommend `ego_graph` primary + optional property/type filters)
- **D-13:** Node detail level in Mermaid diagrams (addressed — recommend id + type + 2-3 distinguishing props, truncated)
- Use case distribution across categories (addressed — propose 7/8/7/7/6 = 35)
- meta.yaml (from Phase 2) is reused; no new format decisions

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DVAL-01 | Use case library covering spatial, social, resource, environmental, edge-case scenarios | §Use Case Library Format, §Use Case Distribution, §Authoring Template |
| DVAL-02 | Gap analysis — review use cases to surface missing mechanics/framework capabilities | §Gap Analysis Workflow, §GAP-ANALYSIS.md Structure |
| GRAPH-06 | Optional R-tree spatial index primitive | §Spatial Index (R-tree), §MechanicContext Integration |
| GRAPH-07 | Optional temporal index primitive | §Temporal Index, §EventStore Wrapper Strategy |
| AUTO-04 | Mermaid diagram generation for graph visualization | §Mermaid Visualization, §CLI Design, §Filtering Strategy |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 3 |
|-----------|-------------------|
| Graph is ground truth | Spatial/temporal indexes are *derived views* — never a parallel source of truth; rebuildable from graph + events |
| Mutation-mediated access | Spatial index updates hook into KnowledgeGraph mutations, not direct NetworkX writes |
| JSON-serializable properties only | Positions stored as `list[float]` (e.g. `[x, y]` or `[minx, miny, maxx, maxy]`), not tuples or numpy arrays |
| No ORM / raw sqlite3 only | Temporal index queries use `sqlite3` parameterized queries against `graph_events` table |
| No pickle | Use case YAML + JSON serialization only |
| Composition over specialization | Spatial/temporal are reusable primitives — not special-cased for movement or time |
| Aggressive subagent delegation | Use case authoring MUST delegate per-case to subagents; orchestrator only coordinates |
| ROI awareness | Gap analysis is the output; don't overbuild indexes/viz if simple approach suffices |
| Dogfooding | `viz-graph` CLI must be useful to agents debugging gap analysis itself |
| `prek` for hooks, `uv` for packages, `ruff`/`mypy` for quality | All Phase 3 code runs through existing tooling |
| Test helpers via `GraphBuilder` | Use case test graphs reuse `GraphBuilder` — do not invent a second builder |

## Use Case Library Format

### Decision: YAML-frontmatter markdown, one file per use case

```
.planning/use-cases/
├── _README.md                     # format spec, authoring guide
├── spatial/
│   ├── UC-S01-movement-through-doorway.md
│   ├── UC-S02-line-of-sight-occlusion.md
│   └── ...
├── social/
│   ├── UC-O01-trade-negotiation.md
│   └── ...
├── resource/
├── environmental/
└── edge-case/
    └── UC-E01-action-against-nonexistent-target.md

.planning/phases/03-design-validation/
└── GAP-ANALYSIS.md                # aggregated summary
```

**Rationale:**
- **Single file per use case** — narrative and structured data live together; impossible to drift out of sync.
- **YAML frontmatter** — Python `pyyaml` (already a dep) parses the header trivially; the markdown body is the narrative.
- **Per-category folders** — maps cleanly onto the parallel wave structure (D-04).
- **Stable IDs** — `UC-<cat-letter><NN>` (S=spatial, O=social/Other-agent, R=resource, V=enVironmental, E=edge-case). Planner assigns IDs up front so authoring agents don't collide.

### Use case file template

```markdown
---
id: UC-S01
category: spatial
title: "Movement through a doorway"
status: draft          # draft | reviewed | locked
setup:
  graph_builder: |
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5,-5,5,5])
    kg.add_node("doorway_1", node_type="entity", subtype="doorway",
                position=[5, 0], connects=["room_a", "room_b"])
    kg.add_node("room_b", node_type="entity", subtype="room", bbox=[5,-5,15,5])
    kg.add_edge("alice", "room_a", relation="located_in")
actions:
  - actor: alice
    intent: "walk east through the doorway into room_b"
    classified:
      verb: move
      direction: east
      target: doorway_1
expected_observations:
  - actor: alice
    narrative_contains: ["room_b", "doorway"]
    graph_assertions:
      - kind: has_edge
        src: alice
        dst: room_b
        relation: located_in
      - kind: not_has_edge
        src: alice
        dst: room_a
        relation: located_in
gaps:
  - layer: mechanic            # graph | mechanic | engine
    severity: address-now      # address-now | defer | out-of-scope
    summary: "No doorway traversal mechanic. Movement seed only handles direct edges between locations, not passing through entity-typed doorways."
    proposed_fix: "Add a `doorway` subtype-aware movement mechanic, or generalize movement to follow `connects` properties on entity nodes."
  - layer: graph
    severity: address-now
    summary: "Need spatial query to find the nearest doorway to alice.position."
    proposed_fix: "Use GRAPH-06 spatial index; mechanic calls ctx.spatial.nearest(alice.position, subtype='doorway')."
---

# UC-S01: Movement through a doorway

## Vignette

Alice stands in the west end of room_a. A stone doorway on the east wall
leads into room_b. She walks through it.

## Why this matters

Tests whether the mechanic framework can handle multi-step spatial reasoning:
identify the relevant doorway, check adjacency, update location edges. Reveals
whether movement needs to be seed-mechanic-simple or generalized to handle
arbitrary passage entities (doors, portals, stairs, ladders).

## Related use cases

- UC-S02 (line-of-sight) — also requires spatial queries
- UC-E03 (move into a locked room) — edge case for this path
```

### Why YAML frontmatter for structured data

- **Machine-parseable** — Phase 6 regression harness loads `yaml.safe_load(frontmatter)` and runs `setup.graph_builder` (as a Python string executed against a fresh `KnowledgeGraph`) + verifies `graph_assertions`.
- **Human-readable** — lives next to the narrative; diffs well in git; agents authoring can verify their own structured pairs against the vignette.
- **Phase 6 contract** — the `actions[]` + `expected_observations[]` pairs become the integration test spec. Each use case produces N pytest parametrize entries.
- **Graph assertions are declarative** — avoids baking Python logic into YAML. The regression runner evaluates a small fixed vocabulary (`has_node`, `has_edge`, `has_property`, `property_equals`, `not_has_edge`, etc.).

**Sources:** `[CITED: pyyaml docs — yaml.safe_load]`, `[VERIFIED: pyproject.toml shows pyyaml>=6.0.3]`

### Use case distribution (~35 total)

Proposed breakdown by category (Claude's discretion per D-02):

| Category | Count | Rationale |
|----------|-------|-----------|
| Spatial | 7 | Most framework-stretching — positions, LOS, containment, adjacency, doorways, trajectories |
| Social | 8 | Most variety — trade, persuasion, deception, teaching, conflict, cooperation, observation, communication |
| Resource | 7 | Conservation-heavy — crafting, consumption, gifting, currency, inventory limits, degradation, fungibility |
| Environmental | 7 | Chain-execution heavy — fire spread, weather, decay, seasons, terrain, light/dark, contagion |
| Edge-case | 6 | Framework robustness — invalid target, concurrent actors, partial knowledge, nonsense input, conservation violation attempts, circular chains |
| **Total** | **35** | |

Each category should have at least one use case that deliberately has **no matching seed mechanic** (per D-03), to surface what the framework is missing.

## Use Case Authoring — Parallel Wave Structure

### Decision: 3-phase wave pattern per category, 5 categories in parallel

```
Wave 0 (serial, 1 task):
  - Write .planning/use-cases/_README.md (format spec, ID scheme, template)
  - Write regression-ready schema validator (validates YAML frontmatter
    against the template)

Wave 1 (5 parallel tasks — one per category):
  - For each category: planning-level task that enumerates N use-case IDs,
    one-line summaries, and assigns each to a category folder.
    Output: .planning/use-cases/<cat>/MANIFEST.md with ID + title + owner slot.

Wave 2 (~35 parallel tasks — one per use case):
  - Each task reads its category MANIFEST + _README template, authors the
    full use-case file (YAML frontmatter + narrative + inline gaps).
    Agents do NOT cross category lines; no shared state between wave-2 tasks
    other than the template.

Wave 3 (5 parallel tasks — one per category):
  - Per-category review + aggregation. Each agent reads every use case in
    its category, sanity-checks the structured pairs (does graph_builder
    produce a graph the actions can run against?), deduplicates gaps, and
    writes <category>/CATEGORY-SUMMARY.md.

Wave 4 (serial, 1 task):
  - Cross-category gap synthesis. Agent reads all CATEGORY-SUMMARY.md files,
    aggregates gaps, re-examines per architecture layer (graph / mechanic /
    engine per D-05), assigns dispositions (per D-06), writes
    GAP-ANALYSIS.md.

(Waves 5-7 handle R-tree, temporal index, viz-graph — see below)
```

### Why this decomposition works

- **No cross-agent collisions in Wave 2** — each author owns exactly one file path. Parallel write conflicts are impossible.
- **Category manifests act as a contract** — Wave 1 sets the scope so Wave 2 agents don't invent redundant or missing cases.
- **Reviews happen inside the category** before cross-category synthesis — catches structural errors (bad YAML, missing fields) without blocking the aggregator agent.
- **Aggregator (Wave 4) is the expensive read** — reads ~35 files at once, but only once. Writing happens in waves 2-3.

**GSD parallelism note:** GSD executes plan tasks in waves based on `dependencies:` declarations. The planner should emit ~35 authoring tasks with `dependencies: [wave-1-<cat>]` so the executor schedules them in one large parallel batch. `[ASSUMED]` — specific GSD wave-batching semantics; planner to confirm against `.claude/commands/gsd-execute-phase.md` if ambiguous.

## Spatial Index (GRAPH-06)

### Decision: Toblerity `rtree` 1.4.1, exposed as lazy `ctx.spatial` accessor

**Verified version:** `rtree 1.4.1` on PyPI; bundles `libspatialindex` in wheels for all major platforms; maintained; no known CVEs. `[VERIFIED: PyPI rtree page, Snyk advisor]`

**Alternatives considered:**

| Option | Verdict | Reasoning |
|--------|---------|-----------|
| Toblerity `rtree` | **Pick** | Pure-C R-tree via `libspatialindex`. Mature (v1.4.1, actively maintained), tiny API, fast (µs per query). Supports 2D/3D/N-D, bounding boxes, nearest-neighbor. |
| `shapely.STRtree` | Reject for v1 | Query-only (read-only, rebuilt each time), and brings in GEOS. Great for static bulk queries, wrong shape for a live-mutating simulation. |
| `scipy.spatial.KDTree` | Reject | Points only (no bounding boxes); also requires rebuild on every mutation. |
| Hand-roll grid hash | Reject | Hits ROI principle: rtree solves this correctly in <100 LOC of integration code. |

### Integration pattern

Expose spatial queries via `MechanicContext` (Phase 2 DSL), not `KnowledgeGraph` directly. Rationale:

1. **Cost-free for mechanics that don't use it.** The index is *not* built on `KnowledgeGraph` construction. It's built lazily on first `ctx.spatial.*` call in a tick, and invalidated when position-mutating events occur.
2. **Matches Phase 2 DSL pattern.** Mechanics already use `ctx.query_node`, `ctx.find_nodes`; `ctx.spatial.nearest(...)` is the natural extension.
3. **Keeps `KnowledgeGraph` minimal.** Phase 1's D-01/D-03 established that the graph stays property-agnostic. Position semantics belong in the DSL layer.

### API shape

```python
# src/token_world/graph/spatial.py

class SpatialIndex:
    """Optional R-tree spatial index over KnowledgeGraph nodes with position data.

    Indexes nodes that have either:
      - position: [x, y]              (point — treated as zero-area bbox)
      - bbox: [minx, miny, maxx, maxy] (axis-aligned 2D bounding box)

    Nodes without position/bbox are simply not indexed.
    Index is rebuildable from graph state; never a source of truth.
    """

    def __init__(self, graph: KnowledgeGraph) -> None: ...

    def rebuild(self) -> None:
        """Scan all nodes, insert every one with position or bbox. O(n log n)."""

    def nearest(self, point: tuple[float, float], *, k: int = 1,
                node_type: str | None = None,
                subtype: str | None = None) -> list[str]:
        """Return up to k nearest node IDs to point."""

    def within(self, bbox: tuple[float, float, float, float], *,
               node_type: str | None = None,
               subtype: str | None = None) -> list[str]:
        """Return node IDs whose position/bbox intersects bbox."""

    def intersects(self, node_id: str, *,
                   node_type: str | None = None,
                   subtype: str | None = None) -> list[str]:
        """Return node IDs whose bbox intersects node_id's bbox (excluding node_id)."""
```

Attached to `MechanicContext`:

```python
# Added to MechanicContext
@property
def spatial(self) -> SpatialIndex:
    if self._spatial is None:
        self._spatial = SpatialIndex(self._graph)
        self._spatial.rebuild()
    return self._spatial
```

**Invalidation:** v1 approach — the context's cached index is valid for the lifetime of a single mechanic `check`+`apply` invocation. Chain execution builds a new context; the next mechanic pays one rebuild cost if it uses spatial. This is simple, correct, and scales to thousands of nodes (rtree bulk-insert of 10k points is <50ms on commodity hardware `[ASSUMED: general rtree perf]`). For v2, incremental invalidation can be added by hooking into `KnowledgeGraph` event emission.

### Coordinate model (v1)

- **2D only.** `position: [x, y]` for points, `bbox: [minx, miny, maxx, maxy]` for regions. Both are `list[float]` (JSON-serializable).
- **3D deferred.** Rtree supports N-dimensional, but v1 use cases don't need Z.
- **Property name convention.** The index reads `position` or `bbox` properties directly — no schema required (Phase 1 D-03 — no framework-enforced node properties). If both exist, `bbox` wins.
- **No CRS/projection.** Units are arbitrary (meters, tiles, abstract). The simulation decides.

### Indexing edges? No

Only nodes are indexed. Edges rarely have intrinsic position in a text simulation; when they do (e.g. a path between locations), the mechanic can represent the path as an `entity` node with `bbox` and an edge to each endpoint.

**Sources:** `[CITED: rtree.readthedocs.io 1.4.1]`, `[CITED: Geoff Boeing blog — R-tree Spatial Indexing with Python]`, `[VERIFIED: pip index versions rtree → 1.3.0 local / 1.4.1 latest on PyPI]`

## Temporal Index (GRAPH-07)

### Decision: Query facade over existing `EventStore` + `graph_events` table — no new storage

The existing infrastructure already records everything a temporal index needs:

| Field | Source | Supports |
|-------|--------|----------|
| `tick_id` | `GraphEvent.tick_id` | Time-range queries |
| `event_type` | `GraphEvent.event_type` | Filter by mutation kind (set_property, add_edge, etc.) |
| `target_id` | `GraphEvent.target_id` | History of a specific node or edge |
| `property_name` | `GraphEvent.property_name` | History of a specific property |
| `old_value_json` / `new_value_json` | `GraphEvent` | State reconstruction at any past tick |

**Rationale:** building a parallel time-series store would violate the "graph is ground truth" principle (CLAUDE.md) — events already *are* the time series.

### API shape

```python
# src/token_world/graph/temporal.py

class TemporalIndex:
    """Query interface over the KnowledgeGraph event log.

    Combines in-memory EventStore (current session) with persistent
    graph_events table (prior sessions). All queries are read-only.
    """

    def __init__(self, graph: KnowledgeGraph) -> None: ...

    def query_history(self, node_id: str, *,
                      tick_range: tuple[int, int] | None = None
                      ) -> list[GraphEvent]:
        """All events targeting node_id, optionally within tick_range (inclusive)."""

    def query_changes(self, property_name: str, *,
                      tick_range: tuple[int, int] | None = None,
                      node_id: str | None = None
                      ) -> list[GraphEvent]:
        """All set_property events for the given property."""

    def find_state_at_tick(self, node_id: str, tick_id: int
                           ) -> dict[str, Any]:
        """Reconstruct a node's property dict as of the end of tick_id.

        Implemented by replaying events from the most recent snapshot at
        or before tick_id. Raises KeyError if the node did not exist then.
        """

    def last_change(self, node_id: str, property_name: str
                    ) -> GraphEvent | None:
        """Most recent set_property event for (node, property), or None."""
```

### Exposure to mechanics

Same pattern as spatial: `MechanicContext.temporal` lazy property. Most mechanics won't touch it; those that do (e.g., "has this property changed in the last 10 ticks?") get a clean DSL hook.

### Performance & scale

- **In-memory session events** — `EventStore` holds ~hundreds to thousands of events between snapshots. Linear scan is fine. `[ASSUMED: based on existing EventStore.get_events implementation]`
- **Historical events** — SQLite `graph_events` table. Add indexes:
  ```sql
  CREATE INDEX IF NOT EXISTS idx_events_tick ON graph_events(tick_id);
  CREATE INDEX IF NOT EXISTS idx_events_target ON graph_events(target_id, tick_id);
  CREATE INDEX IF NOT EXISTS idx_events_property ON graph_events(property_name, tick_id);
  ```
  Raw `sqlite3` parameterized queries only (no ORM — project constraint).
- **`find_state_at_tick`** is the expensive one. Strategy: find the most recent snapshot with `tick_id <= target_tick`, load that node's state from the snapshot blob, then replay events between snapshot tick and target tick. Bounded by the snapshot retention policy (max 50 — Phase 1).

### Why not a separate time-series DB or extra table?

| Option | Verdict | Reason |
|--------|---------|--------|
| New time-series table | Reject | Events already exist; duplication invites drift |
| In-memory sorted structure | Defer | Premature — SQLite indexes + EventStore cover v1 scale |
| External TS DB (InfluxDB, etc.) | Reject | Violates "no server" project constraint |

**Sources:** `[VERIFIED: src/token_world/graph/events.py — GraphEvent has all required fields]`, `[VERIFIED: src/token_world/graph/knowledge_graph.py lines 384-388 — event compaction already tied to snapshot retention]`

## Mermaid Graph Visualization (AUTO-04)

### Decision: `ego_graph` + property filters + node cap, Mermaid `flowchart` output

### Filtering strategy (D-12)

Mandatory anchor selection — one of:
1. `--node <id> --depth N` → `nx.ego_graph(G, n, radius=N, undirected=True)` returns the N-hop neighborhood. `undirected=True` is important — graph is a DiGraph but for visualization we want both directions.
2. `--seed-query <property=value>` → use `kg.nodes(property=value)` to pick seed anchors, union their ego_graphs.
3. `--all-agents` → pick all agent-typed nodes as seeds, depth 1 (high-level orientation view per D-10).

Then apply optional filters on the resulting subgraph:
- `--type agent|entity` — drop nodes of the wrong type (except the anchor)
- `--has-property X` — drop nodes lacking property X
- `--exclude-property Y` — drop nodes with property Y (useful for hiding noise like temperature/stamina on overview diagrams)

**Hard node cap:** if filtered subgraph has >150 nodes, emit an error telling the user to increase `--depth` filter or tighten `--seed-query`. Partial rendering is worse than none — overflowing Mermaid diagrams become unreadable fast.

**Sources:** `[CITED: networkx.org — ego_graph signature (G, n, radius=1, center=True, undirected=False, distance=None)]`

### Node detail level (D-13)

Mermaid flowchart syntax supports node labels like `nodeId["Label text"]`. Decision: **ID + emoji/glyph + 1-2 key props**, styled by type.

```
flowchart LR
    alice["👤 alice<br/>hp=100"]:::agent
    room_a["🏛 room_a<br/>subtype=room"]:::entity
    wallet["🎒 wallet<br/>subtype=container"]:::entity
    alice -- "located_in" --> room_a
    alice -- "holds" --> wallet

    classDef agent fill:#cfe,stroke:#063,color:#000
    classDef entity fill:#fec,stroke:#630,color:#000
```

**Property selection heuristic** (per-node):
1. Always show `type` as an implicit style class (not text).
2. Show `subtype` if present (strong signifier — "room", "weapon", "liquid").
3. Show 1-2 additional "interesting" properties — prioritize short scalars (`hp=100`), skip long strings/lists/dicts.
4. Cap at ~60 chars per label. Truncate with ellipsis.
5. On edges, show the `relation` property if present, else unlabeled arrow.

This balances readability with enough info to debug a mechanic interaction.

### CLI command

```
token-world viz-graph <universe> [OPTIONS]

Options:
  --node ID               Anchor node for ego-graph filter
  --depth N               Hops from --node (default 1, requires --node)
  --seed-query KEY=VALUE  Anchor set: nodes with property KEY=VALUE
                          (repeatable; acts as OR)
  --all-agents            Use all agent-typed nodes as anchors (depth 1)
  --type {agent|entity}   Filter subgraph by type
  --has-property NAME     Include only nodes with this property
  --exclude-property NAME Drop nodes with this property (noise reduction)
  --max-nodes N           Error out if filtered graph exceeds N (default 150)
  --output FILE           Write to file instead of stdout
  --no-style              Emit minimal Mermaid (no classDef, no emoji)
```

**Exit behavior:**
- Refuses with error if none of `--node`, `--seed-query`, `--all-agents` provided.
- Exits non-zero if filtered graph > `--max-nodes`.
- Emits Mermaid markdown (`flowchart LR\n...`) to stdout or file.

### Rendering verification (dogfooding)

The `mcp-mermaid` MCP server is available in the user's Claude environment — see global CLAUDE.md. Agents authoring use cases or debugging gap analysis can pipe the CLI output to mcp-mermaid to visually review diagrams. This aligns with "close the feedback loop" — Mermaid that's not rendered is a hypothesis, not a result.

**Sources:** `[CITED: networkx ego_graph docs]`, `[CITED: mermaid.js.org/syntax/flowchart.html]`, `[VERIFIED: global CLAUDE.md references mcp-mermaid]`

### Why not dot/graphviz?

- Mermaid renders in markdown on GitHub, in VS Code, in most agent docs — zero setup.
- The `mcp-mermaid` server is already in the agent toolchain.
- Graphviz (dot) produces better-looking dense graphs but requires a separate renderer; high-setup cost for v1.

## Gap Analysis (DVAL-02)

### Workflow (implements D-05, D-06, D-07)

```
Step 1: Per-use-case inline gaps (authored in Wave 2)
  Each use case file has a `gaps:` YAML list in frontmatter.
  Each entry: { layer, severity, summary, proposed_fix }

Step 2: Category aggregation (Wave 3)
  Per category: read all use cases, collect all `gaps[]`,
  deduplicate by semantic similarity, write CATEGORY-SUMMARY.md
  (just a gap list with source-UC references).

Step 3: Cross-category synthesis (Wave 4)
  Read all CATEGORY-SUMMARY.md files, reorganize gaps by
  architecture layer (graph / mechanic / engine),
  assign final dispositions (address-now / defer / out-of-scope),
  write GAP-ANALYSIS.md.
```

### GAP-ANALYSIS.md structure

```markdown
# Phase 3: Gap Analysis

**Date:** YYYY-MM-DD
**Use cases surveyed:** 35
**Gaps identified:** N
**Disposition summary:** A address-now, B defer, C out-of-scope

## Executive Summary

[2-paragraph narrative of the main architectural findings]

## Gaps by Architecture Layer

### Graph Layer

| ID | Summary | Severity | Disposition | Source UCs | Proposed Fix |
|----|---------|----------|-------------|-----------|--------------|
| GAP-G01 | No way to query "all nodes within radius" from a given point | high | address-now (this phase, GRAPH-06) | UC-S01, UC-S03, UC-E02 | R-tree spatial index |

### Mechanic Framework Layer

| ID | Summary | Severity | Disposition | Source UCs | Proposed Fix |
|----|---------|----------|-------------|-----------|--------------|
| GAP-M01 | No matcher primitive for "property crossed a threshold" (not just changed) | medium | defer (v2) | UC-V02, UC-V04 | Add ThresholdMatcher in Phase 7 |

### Engine Pipeline Layer

| ID | Summary | Severity | Disposition | Source UCs | Proposed Fix |
|----|---------|----------|-------------|-----------|--------------|
| GAP-E01 | Action classification has no model for multi-target actions ("give sword to bob") | high | address-now (Phase 5 will handle) | UC-O03, UC-O07 | Extend ActionClassification pydantic model with `indirect_object` field |

## Dispositions

### Address Now (Phase 3 or early Phase 4-5)

- GAP-G01 — addressed by GRAPH-06 in this phase
- ...

### Defer (v2 backlog)

- GAP-M01 — threshold matcher, relevant to Phase 7

### Out of Scope

- GAP-X01 — realistic physics simulation (project constraint: text-first)

## Cross-References

By use case: UC-S01 → [GAP-G01, GAP-G05, GAP-M02]
(...full mapping table...)

## Appendix: Gap Severity Scale

- **high** — blocks a core simulation behavior; no viable workaround
- **medium** — workaround exists but is ugly; addressing improves quality
- **low** — nice to have; simulation runs fine without
```

### Gap ID scheme

`GAP-<layer-letter><NN>` — G for graph, M for mechanic, E for engine, X for out-of-scope. Stable across phases so Phase 4/5 planners can cite them.

### Disposition heuristic (for Wave 4 agent)

- If the gap is already on Phase 3's roadmap (spatial, temporal, viz) → **address-now** with reference to the plan task.
- If the gap fits squarely into Phase 4 or 5 (LLM generation, engine pipeline) → **address-now** but tag the target phase. Informs the phase planner.
- If the gap requires v2 multi-agent / hardening / monitoring (REQUIREMENTS.md v2 section) → **defer**.
- If the gap conflicts with project constraints (REQUIREMENTS.md §Out of Scope) → **out-of-scope** with constraint cited.

## Integration with existing MechanicContext DSL

Both new primitives extend `MechanicContext`:

```python
class MechanicContext:
    # existing fields...
    _spatial: SpatialIndex | None = None
    _temporal: TemporalIndex | None = None

    @property
    def spatial(self) -> SpatialIndex:
        if self._spatial is None:
            self._spatial = SpatialIndex(self._graph)
            self._spatial.rebuild()
        return self._spatial

    @property
    def temporal(self) -> TemporalIndex:
        if self._temporal is None:
            self._temporal = TemporalIndex(self._graph)
        return self._temporal
```

**Zero impact on existing mechanics** — no required methods added, just optional accessors. Seed mechanics from Phase 2 (movement, observation, environmental_reaction) continue to work unchanged.

**Test builder integration:** `GraphBuilder` fixture (tests/test_graph/conftest.py) already supports arbitrary kwargs on `.node()`. Positions just work:

```python
graph = (GraphBuilder()
    .node("alice", node_type="agent", position=[0, 0])
    .node("tree", node_type="entity", position=[5, 3])
    .build())
# SpatialIndex built on demand from this graph
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Spatial nearest-neighbor / bbox intersection | Grid hash, KDTree from scratch, brute force O(n²) | `rtree` 1.4.1 | Edge cases in spatial indexing (degenerate boxes, floating-point nearness) are classic footguns. Rtree solves them. |
| Mermaid DSL output | String templating with `f"{src} --> {dst}"` without escaping | A tiny helper module that escapes `"` and `\n` in labels | Mermaid labels break on unescaped quotes and multi-line text. One `escape_mermaid_label()` helper avoids the footgun. |
| Ego-graph filtering | `for n in graph.nodes: if dist(n, anchor) <= depth` | `nx.ego_graph(G, n, radius=N, undirected=True)` | NetworkX has it; handles directed-vs-undirected semantics correctly. |
| YAML frontmatter parsing | Custom `---` split + json.loads | `python-frontmatter` package OR manual `yaml.safe_load` on the top section | Manual split is 10 lines and we already depend on pyyaml; `python-frontmatter` adds a dep for marginal benefit. Choose manual. |
| Use case ID generation | ad-hoc slugs invented per author | Pre-assign IDs in Wave 1 manifest | Prevents collision and renumbering churn. |
| Gap disposition tracking | separate spreadsheet or issue tracker | YAML `severity` + markdown tables in GAP-ANALYSIS.md | Keep ground truth in-repo (CLAUDE.md principle). |

## Architecture Patterns

### Pattern 1: Lazy optional indexes

New indexes attach as `@property` lazy accessors on `MechanicContext`. They rebuild once on first access, and are discarded when the context goes out of scope. Mechanics that don't use them pay zero cost. This is the "composition over specialization" principle (CLAUDE.md): spatial and temporal are orthogonal primitives, not inherited capabilities.

### Pattern 2: Derived views, never ground truth

Spatial and temporal indexes are *read-only projections* of graph state + event log. They are never authoritative. Rebuild from graph any time. This mirrors how `GraphPersistence` is a projection, not a source of truth.

### Pattern 3: Structured-body + narrative-body co-location

The use-case file pattern — YAML frontmatter (structured, machine-consumed) + markdown body (narrative, human-consumed) in the same file — is the same pattern Jekyll/Hugo/Obsidian use. Low invention cost, well understood.

### Pattern 4: Parallel authoring via pre-assigned manifests

The Wave 1 → Wave 2 split (one manifest task per category followed by many author tasks) is a fan-out pattern. Manifest owns the "what gets written where" decision; authors own content. Prevents write conflicts and duplicate work.

### Anti-Patterns to Avoid

- **Markdown + YAML sidecar** — inevitable drift between prose and structured data. Keep them together.
- **Rendering full graphs** — Mermaid dies over 150-200 nodes. Force filtering.
- **Building temporal index as a new table** — duplicates the event log. Query what already exists.
- **Eager spatial index on `KnowledgeGraph`** — non-spatial mechanics pay a cost they don't need. Lazy on context.
- **Non-JSON-serializable positions** — using tuples or numpy arrays breaks persistence round-trip (Phase 1 constraint).

## Common Pitfalls

### Pitfall 1: R-tree needs native library (libspatialindex)

**What goes wrong:** On some Linux systems without a wheel, `pip install rtree` fails with `libspatialindex_c.so: cannot open shared object file`.
**How to avoid:** Prefer the binary wheel (default on PyPI for Linux/macOS/Windows on Python 3.12). Document the fallback: `apt-get install libspatialindex-dev` or `brew install spatialindex`.
**Warning signs:** ImportError at module import time — catch it and emit a helpful message if rtree-dependent code is called.

### Pitfall 2: Mermaid labels break on special characters

**What goes wrong:** Quotes, newlines, and `[]{}()` in node labels break the Mermaid parser.
**How to avoid:** One helper function `escape_mermaid_label(s: str) -> str` that replaces `"` with `#quot;`, newlines with `<br/>`, and truncates at ~60 chars.
**Warning signs:** Diagrams don't render at all, or render with missing nodes. Test early with nodes containing `"`, `\n`, `{`.

### Pitfall 3: `ego_graph` with DiGraph + default undirected=False misses inbound neighbors

**What goes wrong:** KnowledgeGraph wraps `nx.DiGraph`. `ego_graph(G, n, radius=1)` returns only successors. An agent with edges *pointing at it* (e.g. `sword -[held_by]-> alice`) won't show the sword.
**How to avoid:** Always pass `undirected=True` unless the user explicitly wants directionality.
**Warning signs:** Visualizations look suspiciously sparse; nodes you expect to see are missing. `[CITED: networkx.org ego_graph docs]`

### Pitfall 4: Spatial index staleness across chain execution

**What goes wrong:** Mechanic A moves a node. Mechanic B (triggered by chain execution) uses `ctx.spatial.nearest(...)` and gets the pre-move result.
**How to avoid:** Build a fresh `MechanicContext` per mechanic invocation in the chain engine (or explicitly invalidate `_spatial` on context between steps). Document that spatial results are valid within one mechanic invocation only.
**Warning signs:** Chain-execution tests pass individually but fail in certain orderings; results depend on mechanic execution order.

### Pitfall 5: Use case actions referencing non-existent nodes

**What goes wrong:** Author writes an action targeting a node that `setup.graph_builder` didn't create. Regression test in Phase 6 fails with KeyError.
**How to avoid:** Wave 3 per-category review must run a static check: parse every action's `target`/`actor`, verify each appears in setup. Add this to the Wave 0 schema validator.
**Warning signs:** Phase 6 regression suite lights up with KeyError on first run.

### Pitfall 6: `find_state_at_tick` across snapshot compaction

**What goes wrong:** User asks for state at tick 50, but event log only retains events from tick 200+ (Phase 1 event compaction prunes old events past the oldest snapshot).
**How to avoid:** `find_state_at_tick` must check snapshot availability first. If the target tick is before the oldest retained snapshot, raise `TemporalQueryOutOfRange`.
**Warning signs:** Unit tests pass with small histories; breaks on real universes with active snapshot pruning.

### Pitfall 7: Gap analysis becomes a wish list

**What goes wrong:** Authors write 200 gaps, Wave 4 agent can't prioritize, planner can't act on it.
**How to avoid:** Enforce severity field. Wave 4 agent must apply disposition heuristic — if everything is "address-now", something is wrong; majority should be "defer" in a healthy gap analysis.
**Warning signs:** `address-now` count exceeds Phase 4/5 capacity; no clear next action.

## Code Examples

### Mermaid escape helper

```python
# src/token_world/viz/mermaid.py

_ESCAPES = str.maketrans({
    '"': "#quot;",
    "\n": "<br/>",
    "[": "&#91;",
    "]": "&#93;",
})

def escape_label(text: str, *, max_len: int = 60) -> str:
    escaped = text.translate(_ESCAPES)
    if len(escaped) > max_len:
        escaped = escaped[: max_len - 1] + "…"
    return escaped
```

### Ego-graph filter for viz

```python
# src/token_world/viz/graph_viz.py
import networkx as nx

def extract_subgraph(kg: KnowledgeGraph, anchor: str, depth: int) -> nx.DiGraph:
    # Undirected ego_graph for visualization (we want to see both directions)
    return nx.ego_graph(kg._graph, anchor, radius=depth, undirected=True)
# Source: https://networkx.org/documentation/stable/reference/generated/networkx.generators.ego.ego_graph.html
```

### Rtree usage (from official docs)

```python
# Adapted from https://rtree.readthedocs.io/en/latest/tutorial.html
from rtree import index

idx = index.Index()
idx.insert(1, (0.0, 0.0, 1.0, 1.0))  # id, bbox (minx, miny, maxx, maxy)
idx.insert(2, (2.0, 2.0, 3.0, 3.0))
# Nearest
list(idx.nearest((1.5, 1.5, 1.5, 1.5), 1))  # -> [2]
# Intersection
list(idx.intersection((-0.5, -0.5, 0.5, 0.5)))  # -> [1]
```

In our integration, `id` is a small int we map to node_id via a `dict[int, str]` (rtree requires int IDs).

### YAML frontmatter parser (manual)

```python
# src/token_world/use_cases/loader.py
import yaml
from pathlib import Path

def load_use_case(path: Path) -> tuple[dict, str]:
    """Return (frontmatter_dict, markdown_body)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML frontmatter")
    _, fm, body = text.split("---\n", 2)
    return yaml.safe_load(fm), body
```

## Runtime State Inventory

Not applicable — Phase 3 is purely additive (new modules, new CLI subcommands, new docs). No renames, no data migrations, no changes to existing persistence schemas. Temporal index adds indexes to `graph_events` table via `CREATE INDEX IF NOT EXISTS` — idempotent, no rebuild needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All | ✓ | per pyproject.toml | — |
| NetworkX | ego_graph, DiGraph | ✓ | >=3.6 (pyproject.toml) | — |
| PyYAML | use case frontmatter | ✓ | >=6.0.3 (pyproject.toml) | — |
| sqlite3 | temporal queries | ✓ | stdlib | — |
| rtree | spatial index | ✗ (needs install) | 1.4.1 latest | Skip spatial index (make it opt-in via `extras_require`?) |
| libspatialindex | rtree runtime | ✓ typically bundled in wheel | 1.9+ | `apt-get install libspatialindex-dev` on bare Linux |
| mcp-mermaid | render verification (dogfooding) | ✓ | per user's global CLAUDE.md | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** `rtree` — add to `pyproject.toml` as a regular dep (it's core to GRAPH-06). If we want it optional, use `[project.optional-dependencies].spatial = ["rtree>=1.4"]` and import inside `SpatialIndex.__init__` so mechanics that don't use it never trigger the import. **Recommendation:** add to core dependencies — it's small (~200KB wheel) and universally useful.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=9.0 (per pyproject.toml) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DVAL-01 | Every use case file parses to valid frontmatter + body | unit | `uv run pytest tests/test_use_cases/test_schema.py -x` | ❌ Wave 0 |
| DVAL-01 | Every use case `setup.graph_builder` executes cleanly | integration | `uv run pytest tests/test_use_cases/test_setup.py -x` | ❌ Wave 0 |
| DVAL-01 | Every use case action's actor/target exists in setup graph | unit | `uv run pytest tests/test_use_cases/test_references.py -x` | ❌ Wave 0 |
| DVAL-02 | GAP-ANALYSIS.md parses, every gap references ≥1 use case | unit | `uv run pytest tests/test_use_cases/test_gap_analysis.py -x` | ❌ Wave 0 |
| GRAPH-06 | SpatialIndex.nearest returns correct neighbors on sample graph | unit | `uv run pytest tests/test_graph/test_spatial.py::test_nearest -x` | ❌ Wave 0 |
| GRAPH-06 | SpatialIndex.within bbox query | unit | `uv run pytest tests/test_graph/test_spatial.py::test_within -x` | ❌ Wave 0 |
| GRAPH-06 | Nodes without position are not indexed, no error | unit | `uv run pytest tests/test_graph/test_spatial.py::test_missing_position_ok -x` | ❌ Wave 0 |
| GRAPH-06 | ctx.spatial lazy — unused mechanics pay zero cost | unit | `uv run pytest tests/test_mechanic/test_context_spatial.py -x` | ❌ Wave 0 |
| GRAPH-07 | query_history returns events in tick order | unit | `uv run pytest tests/test_graph/test_temporal.py::test_history -x` | ❌ Wave 0 |
| GRAPH-07 | find_state_at_tick reconstructs prior state | unit | `uv run pytest tests/test_graph/test_temporal.py::test_state_at_tick -x` | ❌ Wave 0 |
| GRAPH-07 | TemporalQueryOutOfRange raised past compaction | unit | `uv run pytest tests/test_graph/test_temporal.py::test_past_compaction -x` | ❌ Wave 0 |
| AUTO-04 | `viz-graph` requires an anchor, errors without one | smoke | `uv run pytest tests/test_cli/test_viz_graph.py::test_requires_anchor -x` | ❌ Wave 0 |
| AUTO-04 | `viz-graph --node X --depth 2` emits valid Mermaid flowchart | smoke | `uv run pytest tests/test_cli/test_viz_graph.py::test_ego_output -x` | ❌ Wave 0 |
| AUTO-04 | `viz-graph` exceeds max-nodes → error | smoke | `uv run pytest tests/test_cli/test_viz_graph.py::test_max_nodes -x` | ❌ Wave 0 |
| AUTO-04 | Mermaid labels escape special chars | unit | `uv run pytest tests/test_viz/test_mermaid_escape.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest -v`
- **Phase gate:** Full suite green + `uv run ruff check src/` + `uv run mypy src/token_world/graph/ src/token_world/mechanic/ src/token_world/viz/`

### Wave 0 Gaps

- [ ] `tests/test_use_cases/__init__.py` + `test_schema.py`, `test_setup.py`, `test_references.py`, `test_gap_analysis.py`
- [ ] `tests/test_graph/test_spatial.py` (R-tree index tests)
- [ ] `tests/test_graph/test_temporal.py` (temporal query tests)
- [ ] `tests/test_mechanic/test_context_spatial.py` (DSL integration test)
- [ ] `tests/test_cli/test_viz_graph.py` (CLI smoke tests)
- [ ] `tests/test_viz/__init__.py` + `test_mermaid_escape.py`
- [ ] Framework install: `uv add rtree` — required before GRAPH-06 tests run

## Security Domain

`security_enforcement` is not set in this project; this phase has no authentication, session, input-validation-across-trust-boundary, or cryptography concerns. The use case library is author-controlled markdown+YAML in the repo; no user input crosses a trust boundary. Spatial/temporal indexes read from the graph, which is already internal state.

**One minor concern:** `setup.graph_builder` in use case YAML is a Python code snippet executed by the Phase 6 regression harness. That's an author-trusted code path (committed to the repo, same trust level as test code) — not a user-input trust boundary. Document this clearly: "graph_builder is Python and is executed as such. Treat use case files as committed code, not data."

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | rtree bulk-insert of 10k points is <50ms | Spatial Index — Invalidation | If slower, context rebuild on every mechanic invocation becomes a perf problem — would need incremental invalidation earlier than v2 |
| A2 | GSD executes tasks with `dependencies: []` in parallel waves | Authoring Parallel Wave Structure | If GSD is strictly serial per plan, the 35 authoring tasks run sequentially — slower but still correct |
| A3 | EventStore.get_events linear scan is fine for session-length event lists | Temporal Index — Performance | If session events grow to 100k+ without snapshot compaction, need index on in-memory events too |
| A4 | 150 nodes is the practical Mermaid readability ceiling | Filtering Strategy | If too low, users complain about too-tight filter; if too high, diagrams become noise. Empirically calibrated — adjustable via --max-nodes |
| A5 | All use case graphs fit the 2D position model | Spatial Index — Coordinate Model | If authors want 3D (verticality for flying/climbing), need to extend; deferable since rtree supports N-D natively |
| A6 | Authors can write `graph_builder` Python correctly in YAML | Use Case File Template | If error-prone, may need a more declarative DSL. Wave 3 review catches issues early |

## Open Questions

1. **Should `rtree` be a core dep or `[extras]`?**
   - What we know: rtree is ~200KB, mature, bundles libspatialindex in wheels.
   - What's unclear: whether the project values dependency minimalism enough to make it optional.
   - Recommendation: core dep. Extras create import-gated code that's easy to break.

2. **Does `viz-graph` need a `--format dot` option in addition to Mermaid?**
   - What we know: Mermaid is the agent-native format; mcp-mermaid renders it.
   - What's unclear: whether human operators want static PNGs from Graphviz for docs.
   - Recommendation: defer. Single format, simpler. Add dot later if needed.

3. **Should gap analysis gaps feed directly into Phase 4/5 plans, or just inform them?**
   - What we know: Phase 4/5 plans are not written yet.
   - What's unclear: whether `address-now (Phase 5)` gaps should become tasks or just research inputs.
   - Recommendation: planner should treat them as required research inputs for those phases' `/gsd-research-phase` runs. Tasks still come from the phase planner proper.

4. **Do we store `position` on agent nodes, or only entities?**
   - What we know: Phase 1 says all non-framework properties are emergent.
   - What's unclear: whether agents have positions distinct from "located in a room" edges.
   - Recommendation: both are valid — mechanics decide. Document the pattern: "position = continuous coordinates; located_in edge = discrete containment. Use either or both."

5. **How many of the ~35 use cases should have NO matching seed mechanic?**
   - What we know: per D-03 at least some must go beyond seed mechanics.
   - What's unclear: the right ratio for maximal gap discovery.
   - Recommendation: at least 2 per category (10 total) should fully require gap analysis. The remaining 25 can be "supported today but tests shape of the framework."

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-roll grid-based spatial index | `rtree` via libspatialindex | libspatialindex has been canonical since 2001 | Use rtree, always, for bbox/point spatial queries |
| Separate time-series DB for temporal queries | Event sourcing + indexed event log | Event-sourcing patterns mainstream since 2010s | For append-only audit-log style data, a primary event log + query facade is idiomatic |
| Ad-hoc markdown docs for spec | YAML frontmatter + markdown body | Jekyll/Hugo popularized ~2013; widely used since | Tooling parses both halves — standard stack |
| Graphviz dot-only diagramming | Mermaid in markdown | Mermaid widely supported in GitHub, VS Code, doc sites since ~2020 | Default choice for in-repo diagrams |
| NetworkX full-graph rendering | Ego-graph filtering + caps | NetworkX `ego_graph` existed since 1.0; became idiomatic visualization pattern | Always filter at scale |

**Deprecated/outdated:**
- `pygeos` — merged into `shapely` 2.0. Not relevant here but worth noting for any contributor who remembers it.

## Sources

### Primary (HIGH confidence)

- `src/token_world/graph/knowledge_graph.py` — verified KnowledgeGraph API (Read tool)
- `src/token_world/graph/events.py` — verified GraphEvent fields (Read tool)
- `src/token_world/mechanic/context.py` — verified MechanicContext DSL (Read tool)
- `src/token_world/cli.py` — verified existing CLI pattern (Read tool)
- `tests/test_graph/conftest.py` — verified GraphBuilder signature (Read tool)
- `pyproject.toml` — verified dependencies and Python version (Bash cat)
- NetworkX `ego_graph` docs — https://networkx.org/documentation/stable/reference/generated/networkx.generators.ego.ego_graph.html
- Rtree 1.4.1 docs — https://rtree.readthedocs.io/ (v1.4.1 verified via PyPI)
- Mermaid flowchart syntax — https://mermaid.js.org/syntax/flowchart.html
- PyPI rtree — https://pypi.org/project/rtree/ (v1.4.1 confirmed; Snyk: healthy, no CVEs)

### Secondary (MEDIUM confidence)

- Geoff Boeing — "R-tree Spatial Indexing with Python" https://geoffboeing.com/2016/10/r-tree-spatial-index-python/
- Shapely STRtree docs — https://shapely.readthedocs.io/en/stable/strtree.html (alternative, rejected for v1)
- Obsidian forum — Mermaid maxEdges / render limits

### Tertiary (LOW confidence — unverified but low-risk)

- General perf claim "rtree bulk-insert 10k points <50ms" — A1 in Assumptions Log; should be benchmarked in Phase 3

## Metadata

**Confidence breakdown:**
- Use case format: HIGH — YAML frontmatter pattern is canonical
- Spatial index: HIGH — rtree is the standard; integration pattern follows existing ctx DSL
- Temporal index: HIGH — all required fields already exist on GraphEvent
- Mermaid viz: HIGH — NetworkX ego_graph + Mermaid flowchart are well-understood
- Parallel wave decomposition: MEDIUM — depends on GSD scheduler semantics (A2)
- 150-node Mermaid cap: MEDIUM — calibrated on general Mermaid perf knowledge, adjustable

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (library versions stable, patterns well-established)
