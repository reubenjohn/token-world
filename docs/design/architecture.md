# Architecture Overview

## System Components

```mermaid
graph TD
    subgraph "Operator Layer (Agent Coding Harness)"
        OP["Agent Coding Harness\n(Claude Code / Codex / etc)"]
        SUB["Subagents\n(native harness capability)"]
        FS["File I/O + SQLite\n(direct access to universe folder)"]
    end

    subgraph "Simulation Tools (MCP)"
        RT["resume_tick()\n(starts or resumes a tick)"]
        RB["rollback(snapshot_id)"]
        LM["list_mechanics(filter)"]
        RM["register_mechanic(path)"]
    end

    subgraph "Simulation Engine (Raw API, inside resume_tick)"
        AI["Action Interpreter\n(Haiku)"]
        MM["Mechanic Matcher\n(deterministic)"]
        ME["Mechanic Executor"]
        OG["Observation Generator\n(Sonnet)"]
    end

    subgraph "Universe Folder"
        KG[("Knowledge Graph\n(NetworkX)")]
        DB[("universe.db\n(SQLite)")]
        MF["mechanics/\n(folders in universe git repo)"]
        CF["CLAUDE.md + .mcp.json"]
        TS["tick_summaries/\n(hierarchical JSON)"]
    end

    OP --> RT
    OP --> RB
    OP --> LM
    OP --> RM
    OP --> SUB
    OP --> FS
    RT --> AI
    AI --> MM
    MM -->|"match found"| ME
    MM -->|"no match\n(returns to operator)"| OP
    ME --> KG
    KG --> OG
    OG -->|"tick result"| OP
    KG <--> DB
    ME --> MF
    FS --> DB
    FS --> MF
    FS --> TS
    RM --> MF
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
