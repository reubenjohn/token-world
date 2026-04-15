# Phase 2: Mechanic Framework - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 02-mechanic-framework
**Areas discussed:** Mechanic Protocol Shape, Seed Mechanic Design, Versioning & Registry, CLI Tooling, Chain Execution (emergent)

---

## Mechanic Protocol Shape

### Precondition Return Type

| Option | Description | Selected |
|--------|-------------|----------|
| Bool only | check() returns True/False. Simple, clean. | |
| Result with reasons | check() returns CheckResult(passed, reasons). Richer — engine can explain failures. | ✓ |
| Exceptions for failure | check() returns None on success, raises PreconditionError. Pythonic but controversial. | |

**User's choice:** Result with reasons, but reasons can be empty for mechanics where it's hard or unnecessary to implement.

### apply() Return Type

| Option | Description | Selected |
|--------|-------------|----------|
| List of Mutations | apply() returns list[Mutation]. Clean separation. | ✓ |
| ApplyResult with mutations + hint | apply() returns ApplyResult with observation_hint. Mechanics suggest narration. | |

**User's choice:** List of Mutations (recommended default)
**Notes:** User added that each mechanic needs a unique id and description, and that chain execution traces (a graph of triggered mechanics) should be returned to the engine.

### DSL Style

| Option | Description | Selected |
|--------|-------------|----------|
| Context object | MechanicContext wraps graph, provides query_node(), mutate(), etc. | ✓ |
| Standalone functions | Free functions that take the graph directly. | |

**User's choice:** Context object
**Notes:** User emphasized the need for execution traces given chain mechanics.

---

## Chain Execution (Emergent Requirement)

### Chain Triggering Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Tag-based triggering | Mechanics declare trigger_tags. Engine matches tags to mutations. | |
| Precondition polling | Run check() on ALL involuntary mechanics after every apply(). | |
| Declarative matchers | Involuntary mechanics declare event listeners with framework primitives (spatial, property-change, selector-based). | ✓ |

**User's choice:** Declarative matchers — efficient event listeners, not brute-force polling. Inspired by CSS selectors, JSONPath, or geo-fencing for spatial queries.

### Chain Scope (Phase 2 vs Deferred)

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 2: interface only | Define watches() method but defer chain engine to Phase 5. | |
| Phase 2: full chain engine | Build matcher evaluation, chain execution, max depth, trace tree, cycle detection now. | ✓ |
| You decide | Claude picks scope boundary. | |

**User's choice:** Full chain engine in Phase 2. Initially open to deferring, but reconsidered — "we can't design an open-to-extensibility framework without tackling involuntary mechanics in this phase."

---

## Seed Mechanic Design

### Which Seed Mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Movement | Agent moves between locations. Voluntary. | ✓ |
| Observation | Agent looks around, gathers visible entities. Read-only. | ✓ |
| Pick up / Drop | Agent picks up entity, creating edges. | |
| Environmental reaction | Involuntary — e.g., fire spreads. Tests chain system. | ✓ |

**User's choice:** Movement, Observation, Environmental reaction

### Observation Protocol

| Option | Description | Selected |
|--------|-------------|----------|
| Same protocol, empty apply | Uses check/apply like all mechanics. apply() returns []. | ✓ |
| Separate query mechanic type | QueryMechanic subclass with query() method. | |

**User's choice:** Same protocol, empty apply (recommended default)

---

## Versioning & Registry

### meta.yaml Content

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal metadata | id, description, voluntary, version, author, tags | |
| Rich metadata | Above plus reads/writes properties, dependencies, cost tier | |
| You decide | Claude picks appropriate level | ✓ |

**User's choice:** You decide

### Versioning Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Git commit = version | No semver. Every commit to mechanic folder is a version. | ✓ |
| Explicit semver in meta.yaml | Manual version bumping. | |

**User's choice:** Git commit = version (recommended default)

---

## CLI Tooling

### Which Commands

| Option | Description | Selected |
|--------|-------------|----------|
| list-mechanics | List all mechanics with metadata | ✓ |
| inspect-graph | Dump graph state (raw) | |
| run-mechanic | Execute a mechanic against a universe | ✓ |
| inspect-mechanic | Show source, meta, git history | |

**User's choice:** list-mechanics, run-mechanic
**Notes:** User rejected inspect-mechanic ("file IO and git bash commands suffice") and raw inspect-graph ("imagine graphs with thousands of nodes").

### Graph Inspection Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Query-based inspect | Filters: --type, --has-property, --near, --limit, --stats | ✓ |
| Stats + targeted lookup | Two commands: graph-stats and graph-node | |
| You decide | Claude picks | |

**User's choice:** Both stats and query-based filtering. "Stats is cool, maybe both? You decide."

---

## Claude's Discretion

- meta.yaml content depth
- Mechanic folder location strategy (built-in vs universe-only)
- Matcher primitive API design
- Execution trace data structure
- query-graph output format and filter syntax

## Deferred Ideas

None — all discussion stayed within phase scope.
