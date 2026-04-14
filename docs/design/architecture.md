# Architecture Overview

> **See also:** [simulation-pipeline.md](simulation-pipeline.md) for the detailed per-tick flow,
> including the Phase 7 long-running action continuation branch and the Phase 6 playtest/compression
> plumbing. This page stays high-level on purpose.

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

## Quality

Two canonical discipline docs gate merges and overnight runs:

- **[dashboard-qa-checklist.md](../quality/dashboard-qa-checklist.md)** -- required PR pass for any `src/token_world/dashboard/` change (nine interactive checks + Playwright routine + user-mode cooldown).
- **[sim-quality-rubric.md](../quality/sim-quality-rubric.md)** -- seven-dimension scorecard for "is the run healthy?" CI gate on release-tier overnight runs.

## Phase 4.1: Operator Harness

The operator harness catches simulation yields and drives mechanic authoring via the Claude Agent SDK. Two entry points share the same universe MCP surface and the same mechanic-author subagent definition:

- **Programmatic** — `token-world run-tick` (Click CLI) instantiates `OperatorHarness.handle_yield(signal)` directly; used by automated tests and the Phase-6 playtest runner.
- **Interactive** — a human opens Claude Code inside a universe folder. CLAUDE.md's `Operator Flow: When a Tick Yields` section teaches the outer Claude Code session to invoke the `mechanic-author` subagent (filesystem-defined at `.claude/agents/mechanic-author.md`).

Both paths source their mechanic-author prompt from the same `mechanic_author_prompt(universe, yield_json)` Python function (`src/token_world/operator/subagent.py`), so prompt drift between the two is structurally impossible (T-04.1-22 mitigation).

```mermaid
flowchart TB
    subgraph Engines["Yield sources"]
        Phase5["Phase 5 engine<br/>(not built yet)"]
        Stub["EngineStub<br/>(test-only)"]
    end

    subgraph Entry["Entry points"]
        CLI["token-world run-tick<br/>(Click CLI)"]
        CC["Claude Code<br/>(CLAUDE.md-driven)"]
    end

    Harness["OperatorHarness<br/>(Agent SDK, Opus)"]

    subgraph SDKSession["Outer SDK session"]
        direction LR
        Subagent["mechanic-author<br/>subagent (Opus)"]
        ValTool["validate_mechanic<br/>@tool wrapper"]
        MCP3["3-tool MCP surface<br/>resume_tick · rollback · list_mechanics"]
    end

    Diag["DiagnosticsSink<br/>+ operator/ namespace<br/>(Phase 4.1 extension)"]
    Mechanics["mechanics/*.py<br/>+ tests/"]

    Phase5 -. "YieldSignal" .-> Harness
    Stub -. "YieldSignal (test)" .-> Harness
    CLI --> Harness
    CC --> Harness
    Harness --> Subagent
    Subagent --> ValTool
    Subagent --> Mechanics
    Harness --> MCP3
    Harness --> Diag
```

Key contracts:

- **YieldSignal** (`src/token_world/operator/yield_signal.py`) is the locked interface between engine and operator. Frozen+slots dataclass with 7 fields (`tick_id`, `universe_path`, `schema_version`, `reason`, `action_text`, `classified_action`, `actor_state`, `candidate_mechanic_ids`), deterministic JSON round-trip (`sort_keys=True, indent=2`), schema-versioned rejection on unknown `schema_version` values (T-04.1-01).
- **mechanic-author subagent prompt** (`src/token_world/operator/subagent.py::mechanic_author_prompt`) is the single source of truth for both the programmatic `AgentDefinition` and the per-universe `.claude/agents/mechanic-author.md`. Scaffold writes the filesystem agent during `scaffold_universe()` via `token_world.universe.templates.mechanic_author_agent.render_mechanic_author_md()`.
- **Diagnostics operator namespace** (`src/token_world/operator/diagnostics.py`) extends Phase 4's `DiagnosticsSink` with an `operator/` subfolder per tick. Artefacts: `yield_signal.json`, `authoring_attempts.jsonl`, `validation/attempt_NN.json`, `mechanic_diff.patch`, `resume_outcome.json`. Atomic writes use `tempfile.mkstemp + os.fsync + os.replace` mirroring Phase 4's helper. JSONL appends are tolerant of malformed lines on read. The `OperatorDiagnosticsReader` is the single sanctioned parser (D-16).
- **Subagent tool whitelist** excludes `Agent` (Pitfall 5 / T-04.1-23: subagents must not spawn sub-subagents). Includes `mcp__validation__validate_mechanic` (in-process SDK MCP server wrapping the `validate-mechanic` CLI with `shell=False` — T-04.1-11) and `mcp__token-world__list_mechanics` (from the universe's `.mcp.json`).
- **Safety caps** on the outer session: `max_turns=20` and `max_budget_usd=5.0` (SDK-enforced hard cap per BLOCKER-4 resolution in Plan 03). The integration test asserts `cost_usd < 5.0`.
