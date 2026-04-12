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
        RM["register_mechanic()"]
    end

    subgraph SE["Simulation Engine"]
        direction LR
        AI["Interpreter\n(Haiku)"] --> MM["Matcher"]
        MM -->|match| ME["Executor"]
        MM -->|no match| PAUSE(["⏸ returns to Operator"])
        ME --> KG[("Knowledge\nGraph")]
        KG --> OG["Observer\n(Sonnet)"]
        OG --> DONE(["✓ tick result\nreturns to Operator"])
    end

    UF[("Universe Folder\nuniverse.db · mechanics/ · tick_summaries/")]

    OP --> RT & RB & LM & RM
    RT --> AI
    RM -->|register| UF
    KG <-->|persist| UF
    ME -->|write| UF
    OP -->|"direct file I/O"| UF
```

## Core Simulation Loop

```mermaid
sequenceDiagram
    participant O as Operator (Agent Harness)
    participant E as Simulation Engine
    participant M as Mechanic Registry
    participant G as Knowledge Graph

    O->>E: resume_tick()
    Note over E: Agent produces action text
    E->>E: Interpret & classify action (Haiku)
    E->>M: Find matching mechanic
    alt Mechanic exists
        M-->>E: Return mechanic
        E->>G: Check preconditions
        alt Preconditions met
            E->>G: Apply side effects
            G-->>E: Updated state
            E->>E: Generate observation (Sonnet)
            E-->>O: Tick result + observation
        else Preconditions not met
            E-->>O: Tick result ("preconditions failed")
        end
    else No match — needs new mechanic
        E-->>O: Tick paused ("no mechanic for: fly")
        Note over O: Operator implements mechanic<br/>using file writes + subagents
        O->>M: register_mechanic("mechanics/fly/")
        O->>E: resume_tick() (continues paused tick)
        E->>G: Execute new mechanic
        E-->>O: Tick result + observation
    end
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
```
