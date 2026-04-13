# Architecture Overview

## System Components

```mermaid
graph TB
    subgraph OL["Operator Layer"]
        OP["Agent Harness\n(Claude Code / Codex)"]
    end

    subgraph MCP["MCP Tools"]
        direction LR
        RT["resume_tick()"]
        RB["rollback()"]
        LM["list_mechanics()"]
    end

    subgraph SE["Simulation Engine"]
        SC["Scheduler"] -->|"prior observations\n+ context"| RA["Resident Agent\n(Haiku)"]
        RA -->|"action text"| AI["Interpreter\n(Haiku)"]
        AI -->|"classified action"| MM["Matcher"]
        MM -->|match| ME["Executor"]
        MM -->|no match| PAUSE(["⏸ returns to Operator"])
        ME -->|"mutations"| KG[("Knowledge\nGraph")]
        KG -->|"updated state"| OG["Observer\n(Sonnet)"]
        OG --> DONE(["✓ tick result + observation"])
    end

    UF[("Universe Folder\nuniverse.db · mechanics/ · tick_summaries/")]

    OP --> RT & RB & LM
    RT --> SC
    RT -->|auto-scan mechanics/| UF
    KG <-->|persist| UF
    ME -->|write| UF
    OP -->|"direct file I/O"| UF
```

## Core Simulation Loop

```mermaid
sequenceDiagram
    participant O as Operator (Agent Harness)
    participant E as Simulation Engine
    participant A as Resident Agent (Haiku)
    participant M as Mechanic Registry
    participant G as Knowledge Graph

    O->>E: resume_tick()
    Note over E: Scheduler determines agent execution order

    loop For each scheduled agent
        E->>G: Query agent context + prior observations
        G-->>E: Agent state
        E->>A: Feed observations + context
        A-->>E: Action text (free-form)
        E->>E: Interpret & classify action (Haiku)
        E->>M: Find matching mechanic
        alt Mechanic exists
            M-->>E: Return mechanic
            E->>G: Check preconditions
            alt Preconditions met
                E->>G: Apply mutations
                G-->>E: Updated state
                E->>E: Generate grounded observation (Sonnet)
                E->>A: Deliver observation to agent memory
            else Preconditions not met
                E-->>O: Tick result ("preconditions failed")
            end
        else No match — needs new mechanic
            E-->>O: Tick paused ("no mechanic for: fly")
            Note over O: Operator authors mechanics/fly.py<br/>using file writes + subagents
            O->>E: resume_tick() (auto-scans mechanics/, validates, continues paused tick)
            E->>M: Discover & register mechanics/fly.py
            E->>G: Execute new mechanic
            G-->>E: Updated state
            E->>E: Generate grounded observation (Sonnet)
            E->>A: Deliver observation to agent memory
        end
    end

    E-->>O: Tick result + observations
    O->>O: Write tick summary to tick_summaries/
```

## Mechanic Structure

```mermaid
classDiagram
    class Mechanic {
        +str name
        +str description
        +int version
        +check(graph, context) bool
        +apply(graph, context) list~Mutation~
    }

    class KnowledgeGraph {
        +query(node, property) Any
        +set(node, property, value) Mutation
        +add_node(id, **props) Mutation
        +add_edge(src, dst, **props) Mutation
        +snapshot() GraphState
        +restore(snapshot) void
    }

    class MechanicContext {
        +KnowledgeGraph kg
        +SpatialIndex spatial
        +TemporalIndex temporal
    }

    class SpatialIndex {
        +nearest(point, k, ...) list
        +within(bbox, ...) list
        +intersects(node_id, ...) list
    }

    class TemporalIndex {
        +query_history(node_id, tick_range) list
        +query_changes(property, ...) list
        +find_state_at_tick(node_id, tick) dict
        +last_change(node_id, property) Event?
    }

    class Mutation {
        +str type
        +str target
        +str property
        +Any old_value
        +Any new_value
    }

    Mechanic ..> KnowledgeGraph : queries/mutates
    Mechanic ..> Mutation : produces
    KnowledgeGraph ..> Mutation : applies
    Mechanic ..> MechanicContext : reads
    MechanicContext --> KnowledgeGraph
    MechanicContext --> SpatialIndex : lazy
    MechanicContext --> TemporalIndex : lazy
    SpatialIndex ..> KnowledgeGraph : rebuilds from
    TemporalIndex ..> KnowledgeGraph : replays events of
```

## Spatial & Temporal Primitives

Mechanics reach the graph through `MechanicContext`. Two lazy accessors extend the DSL without adding cost to mechanics that don't use them:

- **`ctx.spatial`** -- R-tree-backed queries (`nearest`, `within`, `intersects`) over nodes with `position=[x, y]` or `bbox=[x1, y1, x2, y2]` properties. Malformed coords are logged and skipped, not raised.
- **`ctx.temporal`** -- Event-log queries (`query_history`, `query_changes`, `find_state_at_tick`, `last_change`) over the mem+disk-merged event stream. Reconstructs node state at any reachable tick via snapshot baseline + event replay.

Both are pay-for-what-you-use: `ctx._spatial` / `ctx._temporal` stay `None` until first access.

## Operator Tooling

- **`token-world create <slug>`** -- scaffold a new universe folder.
- **`token-world list`** -- enumerate known universes.
- **`token-world viz-graph <slug>`** -- render the knowledge graph as a Mermaid `flowchart LR` with category styling, label/ID sanitisation, and filters (`--node`, `--depth`, `--type`, `--has-property`, `--exclude-property`, `--max-nodes`). See the [viz-graph guide](../guides/viz-graph.md).
