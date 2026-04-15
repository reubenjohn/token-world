# Phase 3: Design Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 03-design-validation
**Areas discussed:** Use case design, Gap analysis process, Optional indexes, Graph visualization

---

## Use Case Design

### Concreteness Level

| Option | Description | Selected |
|--------|-------------|----------|
| Action-observation pairs | Structured format: given graph state X, agent does Y, expect observation Z and mutations W. Directly testable. | |
| Narrative vignettes | Story-style scenarios describing expected behavior. More readable, less precise. | |
| Both layers | Narrative vignette for human understanding + structured action-observation pairs for machine testing. | ✓ |

**User's choice:** Both layers
**Notes:** None

### Scenario Count

| Option | Description | Selected |
|--------|-------------|----------|
| 3-5 per category | ~20 total use cases. Enough to surface gaps without becoming a maintenance burden. | |
| 5-8 per category | ~35 total. More thorough coverage. | |
| You decide | Claude picks appropriate depth per category based on complexity. | ✓ (modified) |

**User's choice:** "You decide but 35 seems reasonable. I suspect we might need dedicated agents for each category or even each case to be launched in waves."
**Notes:** User wants ~35 total with Claude deciding distribution. Flagged need for parallel agent waves in implementation.

### Scope Beyond Seeds

| Option | Description | Selected |
|--------|-------------|----------|
| Beyond seeds | Use cases cover full range (crafting, trading, combat, etc.) even without existing mechanics. Gap analysis finds what's missing. | ✓ |
| Seed mechanics only | Only write cases for Movement, Observation, Environmental Reaction. | |
| Seeds + one layer out | Cover seeds plus immediate extensions. | |

**User's choice:** Beyond seeds (Recommended)
**Notes:** None

---

## Gap Analysis Process

### Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Per use case | Each use case identifies needed mechanics/capabilities. Gaps emerge naturally. | |
| Per architecture layer | Review graph API, mechanic protocol, engine pipeline separately. | |
| Both perspectives | Per-use-case identification, then aggregate per architecture layer. Most thorough. | ✓ |

**User's choice:** Both perspectives
**Notes:** None

### Gap Dispositions

| Option | Description | Selected |
|--------|-------------|----------|
| Three-way | Address now, Defer, Out of scope. Simple and actionable. | ✓ |
| Four-way with priority | Critical, Important, Nice-to-have, Out of scope. More granular. | |
| You decide | Claude picks the disposition scheme. | |

**User's choice:** Three-way (Recommended)
**Notes:** None

### Output Format

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone report | Separate GAP-ANALYSIS.md with all gaps aggregated. | |
| Inline + summary | Each use case notes its own gaps, plus a summary report that aggregates them. | ✓ |
| You decide | Claude picks the format. | |

**User's choice:** Inline + summary
**Notes:** None

---

## Optional Indexes

### Spatial Index Integration

| Option | Description | Selected |
|--------|-------------|----------|
| DSL method on context | ctx.query_nearby(node_id, radius). Lazy-loaded R-tree. | |
| Separate SpatialIndex object | Standalone index mechanics instantiate explicitly. | |
| You decide | Claude picks the integration pattern. | ✓ |

**User's choice:** You decide
**Notes:** None

### Temporal Index Design

| Option | Description | Selected |
|--------|-------------|----------|
| Event-time queries | Query EventStore by tick range and node. Builds on existing infrastructure. | |
| Time-series properties | Nodes have time-indexed property values. Richer but more complex. | |
| You decide | Claude picks the temporal query model. | ✓ |

**User's choice:** You decide
**Notes:** None

---

## Graph Visualization

### Primary Purpose

| Option | Description | Selected |
|--------|-------------|----------|
| Debugging/inspection | Operator sees local neighborhood. Always filtered, never whole-graph. | |
| Architecture overview | High-level topology: agents, major locations, connectivity patterns. | |
| Both | Local neighborhood + high-level summary. Two visualization modes. | ✓ |

**User's choice:** Both
**Notes:** User noted upfront: "Mermaid is probably a bad idea without filters, etc because of how large these graphs can be. Side note: Please document these knowledge graphs can contain thousands of nodes."

### Invocation Method

| Option | Description | Selected |
|--------|-------------|----------|
| CLI command | viz-graph <universe> --node <id> --depth 2. Outputs Mermaid markdown. | ✓ |
| Python API only | kg.to_mermaid() returns Mermaid string. No CLI wrapper. | |
| Both CLI + API | Python API + CLI wrapping it. | |

**User's choice:** CLI command (Recommended)
**Notes:** None

### Filtering Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Ego-graph | Center on node, expand N hops. NetworkX ego_graph() built in. | |
| Query-based | Filter by node type, property values, edge types. | |
| You decide | Claude picks the filtering strategy. | ✓ |

**User's choice:** You decide
**Notes:** None

### Node Detail Level

| Option | Description | Selected |
|--------|-------------|----------|
| ID + type + key properties | Node label shows ID, type, plus 2-3 relevant properties. | |
| ID + type only | Minimal labels. | |
| You decide | Claude picks detail level. | ✓ |

**User's choice:** You decide
**Notes:** None

---

## Claude's Discretion

- Spatial index integration pattern (D-08)
- Temporal index design (D-09)
- Graph visualization filtering strategy (D-12)
- Node detail level in Mermaid diagrams (D-13)
- Use case distribution across categories

## Deferred Ideas

None — discussion stayed within phase scope.
