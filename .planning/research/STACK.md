# Technology Stack

**Project:** Token World - LLM-powered procedural universe simulation
**Researched:** 2026-04-11
**Overall Confidence:** MEDIUM-HIGH

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Python | 3.12+ | Engine language | Rich AI/ML ecosystem, target for LLM code generation, excellent library support. 3.12+ for performance improvements and better error messages. | HIGH |
| NetworkX | 3.6.1 | In-memory knowledge graph | Schema-less by design -- nodes/edges accept arbitrary key/value attributes with no schema declaration. Dict-of-dicts adjacency structure enables fast addition/deletion/lookup. Battle-tested, massive algorithm library, and the standard Python graph library. JSON serialization built in via `networkx.readwrite.json_graph`. | HIGH |
| SQLite | 3.45+ (bundled) | Persistence layer | Zero-config embedded database. JSON1 extension enables querying JSON columns. Perfect for hobby project -- no server to manage. Supports the snapshot/versioning pattern via append-only event tables. | HIGH |
| Anthropic Python SDK | 0.80+ | LLM API access | Direct API access for structured outputs, tool use, and code generation prompts. Structured outputs now GA for Sonnet/Opus/Haiku. Gives full control over prompt construction and token usage -- critical for cost optimization. | HIGH |

### Agent Framework

**Hybrid approach** (decided in PROJECT.md):
- Agent SDK (e.g. Claude Code, Codex) sits at the top as operator/collaborator — orchestrates the simulation, handles mechanic generation (iterative coding), and enables human collaboration via shared tool interface
- Raw Anthropic Python SDK powers the deterministic pipeline calls inside tools (action classification via Haiku, mechanic matching, observation formatting via Sonnet)
- Simulation exposed as minimal MCP tools: `resume_tick` (start or resume a tick, including partially executed ones), `rollback`, `list_mechanics`, `register_mechanic`. Operator accesses universe state directly via filesystem and SQLite — no wrapper tools needed for inspection.
- Harness-agnostic — works with any agent coding harness that reads CLAUDE.md/AGENTS.md + MCP

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Claude Agent SDK | latest | Top-level orchestration — mechanic generation loop, human collaboration, simulation tool dispatch | Agent SDK sits at the operator layer; mechanic generation benefits from its iterative coding loop and tool-use capabilities. Human can collaborate via the same tool interface. | HIGH |
| Anthropic Python SDK (raw API) | 0.80+ | Deterministic pipeline calls inside simulation tools — action classification, mechanic matching, observation formatting | Direct `client.messages.create()` calls with full control over model, system prompt, and tools per call. The inner pipeline is a deterministic orchestrator — raw API is the right abstraction here. | HIGH |

**Key implementation details:**
- Per-call model routing: `model="claude-opus-4-6"` for mechanic generation, `model="claude-sonnet-4-6"` for engine/observation, `model="claude-haiku-4-5-20251001"` for classification
- Structured outputs (JSON mode) eliminate parsing issues
- Full control over system prompts, temperature, token budgets, and retry logic per call type
- Thin custom session persistence layer (~50-100 LOC) for resident agent memory: save/load message arrays as JSONL, fork = copy + truncate
- Hierarchical tick summaries (JSON in tick_summaries/) enable agent catch-up after compaction or handoff: tick → batch (100 ticks) → epoch (100 batches)

### Persistence Layer

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| SQLite (via Python `sqlite3`) | stdlib | Graph state, mechanic storage, event log | Zero dependency. JSON columns for flexible node/edge properties. WAL mode for concurrent reads. Custom persistence layer wrapping NetworkX is ~200 lines of code and gives exact control over serialization format. | HIGH |
| Custom event log (append-only table) | N/A | Graph state versioning, snapshots, rollback | Event sourcing pattern without the `eventsourcing` library. Each graph mutation is logged as an event (node_added, edge_added, property_set, etc.) with a monotonic sequence number. Snapshots are periodic full JSON dumps of the NetworkX graph. Simple, debuggable, no framework overhead. | MEDIUM-HIGH |

**Why NOT a dedicated graph database:**
- Neo4j, Memgraph, FalkorDB all require running a server -- unnecessary overhead for a hobby project with a single agent.
- NetworkX in-memory + SQLite persistence gives the best of both worlds: fast in-memory graph operations with durable storage.
- The graph will be small enough (hundreds to low thousands of nodes) to fit entirely in memory for the foreseeable future.

### Mechanic Sandboxing

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| RestrictedPython | 8.2 | AST-level code restriction | Compiles generated Python through a restricted AST transformer. Blocks dangerous operations (file I/O, network, imports) at compile time. Supports Python 3.9-3.13. Use as the first line of defense for generated mechanic code. | MEDIUM |
| `subprocess` with resource limits | stdlib | Process isolation fallback | For mechanics that need broader Python features, run in a subprocess with `resource` limits (CPU time, memory). Combined with RestrictedPython for defense-in-depth. | MEDIUM |

**Why NOT Docker/container sandboxing:**
- Massive overhead for executing small mechanic functions (precondition check + side effect).
- Mechanics operate on a controlled API surface (graph query/mutation primitives). The attack surface is small.
- RestrictedPython + controlled builtins + a well-defined mechanic API is sufficient for v1.
- Container sandboxing can be added later if mechanics become more complex.

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| Pydantic | 2.12+ | Data validation, structured output schemas | Define schemas for mechanic signatures, graph query results, LLM structured outputs. Rust-backed validation is fast. Native Anthropic SDK integration. | HIGH |
| pytest | 8.x | Testing | Unit tests for mechanics, integration tests for the simulation loop. | HIGH |
| python-dotenv | 1.x | Environment config | API keys, model selection, debug flags. | HIGH |
| loguru | 0.7+ | Structured logging | Better than stdlib logging. Simulation events need clear, structured logs for debugging emergent behavior. | MEDIUM |
| rich | 13.x | Terminal output | Formatted simulation output, debug displays, graph state inspection during development. | LOW (nice-to-have) |
| deepdiff | 7.x | Graph state diffing | Compare graph snapshots for debugging. Detect what changed between simulation steps. | MEDIUM |
| click | 8.x | CLI interface | Run simulations, inspect state, replay from snapshots. Simple CLI over the engine. | MEDIUM |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Package management, virtual environments | Fast, modern Python package manager. Replaces pip + venv + pip-tools. |
| ruff | Linting + formatting | Replaces flake8 + black + isort. Fast (Rust-based). |
| mypy | Type checking | Critical for the mechanic framework API -- generated code must match expected types. |
| prek | Git hooks | Run ruff + mypy before commits. |

## Architecture of Persistence Layer

```
NetworkX DiGraph (in-memory, runtime)
    |
    v
Persistence Adapter (custom, ~200 LOC)
    |
    +-- graph_snapshots table (periodic full JSON dump)
    +-- graph_events table (append-only mutation log)
    +-- mechanics table (code text + metadata + version)
    +-- mechanic_versions table (full history)
    +-- agent_state table (personality, memory, history)
    +-- simulation_log table (action -> mechanic -> result)
    |
    v
SQLite file (single .db file, WAL mode)
```

**Snapshot + event log pattern:**
1. On startup: load latest snapshot into NetworkX
2. Replay any events after that snapshot
3. During simulation: log each graph mutation as an event
4. Periodically: dump full graph state as a new snapshot
5. For rollback: load snapshot N, replay events up to desired point

## Installation

```bash
# Project setup
uv init token-world
cd token-world

# Core dependencies
uv add anthropic networkx pydantic python-dotenv

# Sandboxing
uv add RestrictedPython

# Development
uv add --dev pytest ruff mypy prek loguru rich deepdiff click

# Optional: type stubs
uv add --dev types-networkx
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Graph library | NetworkX | Neo4j / Memgraph / FalkorDB | Server overhead, unnecessary for hobby project scale. NetworkX's in-memory dict-of-dicts is faster for small graphs. |
| Graph library | NetworkX | simple-graph-sqlite | Last updated 2022 (v2.1.0). Limited query capabilities. NetworkX has vastly superior algorithm library. |
| Graph library | NetworkX | kglab | Adds RDF/SPARQL complexity. Token World needs property graph semantics, not RDF triples. |
| Persistence | SQLite (custom layer) | PostgreSQL | Server dependency. SQLite is sufficient and simpler for single-process simulation. |
| Persistence | SQLite (custom layer) | eventsourcing library | Heavy framework for what is ~200 lines of custom code. The library targets enterprise DDD patterns, not graph state tracking. |
| Agent framework | Hybrid (Agent SDK + Raw API) | Claude Code SDK (subprocess) | Subprocess overhead per call, opaque token spend, fights per-call model routing, autonomous loop conflicts with deterministic engine pipeline. |
| Agent framework | Hybrid (Agent SDK + Raw API) | LangGraph | Overkill for single-agent loop. Graph-based orchestration adds complexity without benefit until multi-agent (v2+). |
| Agent framework | Hybrid (Agent SDK + Raw API) | CrewAI | Role-based multi-agent framework. Wrong abstraction for a simulation engine. |
| Sandboxing | RestrictedPython | Docker containers | ~100ms+ overhead per execution vs. microseconds for RestrictedPython. Mechanics run frequently in tight loops. |
| Sandboxing | RestrictedPython | PyPy sandbox | No longer maintained. |
| Sandboxing | RestrictedPython | Pyodide (WASM) | Complex setup, limited library support in WASM environment, overkill for controlled mechanic API. |
| Package manager | uv | pip / poetry | uv is 10-100x faster, handles venvs natively, actively developed by Astral (ruff creators). |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| LangChain | Massive abstraction layer with frequent breaking changes. Adds complexity for simple LLM calls. Token World needs precise prompt control, not LangChain's chain abstractions. | Hybrid (Agent SDK + Raw API) with Pydantic for structured outputs |
| MongoDB | Server dependency, overkill for single-file persistence. JSON-in-SQLite gives the same flexibility. | SQLite with JSON columns |
| Neo4j | Requires running a JVM-based server. Cypher query language is another thing to learn/generate. NetworkX queries are just Python. | NetworkX (in-memory) + SQLite (persistence) |
| FastAPI / Flask | No web server needed for v1. The simulation is a CLI/script, not a web app. | click for CLI interface |
| LangGraph | Graph-based agent orchestration adds complexity. v1 is a single agent with a deterministic tool loop. | Hybrid (Agent SDK + Raw API) |
| CrewAI | Multi-agent role framework. Wrong level of abstraction. | Hybrid (Agent SDK + Raw API) |
| Celery / task queues | No async task processing needed for single-agent synchronous simulation. | Direct function calls |
| ORM (SQLAlchemy) | The graph persistence layer is custom by nature (JSON blobs, event logs). An ORM adds mapping complexity without benefit. | Raw sqlite3 with parameterized queries |
| pickle for persistence | Not human-readable, version-fragile, security risk with untrusted data. | JSON serialization via NetworkX's json_graph module |

## Model Selection Strategy

| Task | Recommended Model | Why | Cost Notes |
|------|-------------------|-----|------------|
| Action interpretation (classify what agent is doing) | Claude Haiku 4.5 | Fast, cheap, sufficient for classification | Lowest cost per call |
| Mechanic selection (match action to existing mechanic) | Claude Haiku 4.5 | Structured matching task, doesn't need deep reasoning | Low cost |
| Mechanic generation (write new Python code) | Claude Opus 4.6 (via Agent SDK) | Highest quality code generation — mechanics are the core value; quality justifies cost. Agent SDK's iterative coding loop handles retries and refinement. | Higher cost, use structured outputs |
| Resident agent (personality, decisions) | Claude Haiku 4.5 | Personality expression doesn't need deep reasoning | Keep agent costs low for future scaling |
| Complex world-building decisions | Claude Sonnet 4.6 | When coherence across many mechanics matters | Use sparingly |

**Cost principle:** Use the cheapest model that produces acceptable quality for each task. Haiku for classification/matching, Opus for mechanic generation (core value justifies cost), Sonnet for complex decisions.

## Sources

- [NetworkX 3.6.1 documentation](https://networkx.org/documentation/stable/) - HIGH confidence
- [NetworkX JSON serialization](https://networkx.org/documentation/stable/reference/readwrite/json_graph.html) - HIGH confidence
- [Anthropic Python SDK (PyPI)](https://pypi.org/project/anthropic/) - HIGH confidence
- [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) - HIGH confidence
- [Claude Agent SDK (PyPI)](https://pypi.org/project/claude-agent-sdk/) - v0.1.58, HIGH confidence
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - HIGH confidence
- [RestrictedPython documentation](https://restrictedpython.readthedocs.io/) - v8.2, HIGH confidence
- [RestrictedPython (PyPI)](https://pypi.org/project/RestrictedPython/) - HIGH confidence
- [Pydantic documentation](https://docs.pydantic.dev/latest/) - v2.12+, HIGH confidence
- [SQLite JSON1 extension](https://sqlite.org/json1.html) - HIGH confidence
- [AI Agent Frameworks Compared 2026](https://letsdatascience.com/blog/ai-agent-frameworks-compared) - MEDIUM confidence
- [Code Sandboxes for LLMs](https://amirmalik.net/2025/03/07/code-sandboxes-for-llm-ai-agents) - MEDIUM confidence
- [simple-graph-sqlite (PyPI)](https://pypi.org/project/simple-graph-sqlite/) - v2.1.0, last updated 2022, HIGH confidence (version verified)
- [eventsourcing (PyPI)](https://pypi.org/project/eventsourcing/) - v9.5.4, MEDIUM confidence
- [NetworkX persistence challenges](https://memgraph.com/blog/data-persistency-large-scale-data-analytics-and-visualizations-biggest-networkx-challenges) - MEDIUM confidence
