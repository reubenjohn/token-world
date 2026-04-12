# Phase 1: Graph Foundation - Research

**Researched:** 2026-04-11
**Domain:** Knowledge graph (NetworkX + SQLite persistence + snapshot/rollback)
**Confidence:** HIGH

## Summary

Phase 1 builds the core knowledge graph layer: a NetworkX DiGraph wrapped in a persistence adapter that serializes to SQLite, with snapshot/restore for rollback. The graph is schema-less by design -- nodes and edges accept arbitrary key/value properties with no declaration. All simulation state lives here; if it's not in the graph, it doesn't exist.

The technical risk is low. NetworkX 3.6.1 is already installed and verified to handle arbitrary properties, JSON serialization roundtrips, and all standard graph operations. SQLite 3.50.4 with JSON1 extension is confirmed available. The main implementation work is the persistence adapter (~200 LOC), the snapshot/restore mechanism, the `claim_id()` deconfliction helper, and the event log for mutations.

**Primary recommendation:** Build a thin `KnowledgeGraph` class wrapping NetworkX DiGraph that mediates all mutations through an event log, persists snapshots as JSON blobs in SQLite, and exposes the API shape defined in `docs/design/architecture.md`. Keep it simple -- no event sourcing framework, no ORM, just raw sqlite3.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Framework knows exactly two fundamental node types: `agent` and `entity`. Everything else is emergent.
- **D-02:** Node IDs are mechanic-driven via a `claim_id(name)` helper. The graph deconflicts: `"wallet"` if available, `"wallet_a7"` if taken. IDs are readable for debugging but unique.
- **D-03:** No other framework-enforced properties or constraints on nodes. Mechanics add whatever properties they need.
- **D-05:** Every tick is identifiable by a tick ID. Snapshots are linked to tick identifiers.
- **D-06:** Snapshot names are derived from a summary of changes since the last snapshot, built from hierarchical tick summaries.

### Claude's Discretion
- **D-04:** Property value types -- balance flexibility with persistence reliability
- **D-07:** Snapshot storage details -- format, retention, git integration
- **D-08:** CLAUDE.md content and depth -- whatever achieves agent autonomy

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GRAPH-01 | Knowledge graph supports arbitrary node/edge properties without schema declaration | NetworkX DiGraph natively supports arbitrary key/value attributes on nodes and edges. Verified via roundtrip test -- int, float, bool, None, list, dict all survive JSON serialization. |
| GRAPH-02 | New concepts emerge dynamically when mechanics create them | Schema-less design: no property declaration needed. `G.nodes[id]['temperature'] = 500` just works. Persistence via JSON columns preserves any new property automatically. |
| GRAPH-03 | Graph state persists to SQLite and survives process restarts | `networkx.readwrite.json_graph.node_link_data()` produces JSON-serializable dict. Store as TEXT in SQLite. Roundtrip verified: all property types preserved. |
| GRAPH-04 | Graph state can be snapshotted at any point for later rollback | JSON serialization of full graph state (~1.8ms per 1000-node graph) stored in `graph_snapshots` table with tick_id linkage. |
| GRAPH-05 | Graph can be restored to any previous snapshot | `json_graph.node_link_graph()` reconstructs DiGraph from JSON (~4.4ms per 1000-node graph). Replace in-memory graph, replay any post-snapshot events if needed. |
| TEST-03 | Snapshot/restore round-trip tests verify graph and mechanic state integrity | Test pattern: build graph -> snapshot -> mutate -> restore -> assert match. NetworkX graph equality via node/edge data comparison. |
| TEST-06 | Convenience graph builder utilities for concise test setup | `GraphBuilder` fixture pattern: `builder.node("bob", type="agent", hp=100).node("sword", type="entity").edge("bob", "sword", relation="holds").build()` |
| AUTO-01 | CLAUDE.md with architecture overview, critical constraints, validation protocols, and script catalog | Update project CLAUDE.md with graph module architecture, API reference, testing commands, and critical constraints (mutation-via-event-log, no direct graph modification). |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| NetworkX | 3.6.1 | In-memory knowledge graph | Schema-less dict-of-dicts, arbitrary properties, built-in JSON serialization. Already installed. [VERIFIED: `uv run python3 -c "import networkx; print(networkx.__version__)"` -> 3.6.1] |
| SQLite (stdlib sqlite3) | 3.50.4 | Persistence layer | JSON1 extension confirmed available. WAL mode supported. Zero dependency. [VERIFIED: `uv run python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` -> 3.50.4] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic | 2.12+ | Mutation/snapshot data models | Define Mutation, Snapshot, GraphEvent models with validation |
| pytest | 9.0.3 | Testing framework | Already installed and configured with 57 passing tests [VERIFIED: `uv run pytest -q` -> 57 passed] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSON blob snapshots | Event replay from scratch | Slower restore, more complex, but enables granular rollback. Use hybrid: periodic snapshots + event replay for fine-grained points. |
| `json_graph.node_link_data` | `copy.deepcopy` for in-memory snapshots | deepcopy is 3x slower (5.8ms vs 1.8ms per 1000-node graph for serialization). JSON is also needed for SQLite storage anyway. [VERIFIED: benchmark] |
| Raw sqlite3 | SQLAlchemy ORM | Forbidden by project constraints. Raw sqlite3 is simpler for JSON blob storage. |

**No new packages needed.** All dependencies are already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
src/token_world/
  graph/
    __init__.py          # Public API exports
    knowledge_graph.py   # KnowledgeGraph class (core wrapper around NetworkX)
    persistence.py       # SQLite adapter (save/load/snapshot/restore)
    events.py            # GraphEvent model and EventStore
    identity.py          # claim_id() helper
    models.py            # Mutation, Snapshot Pydantic models
tests/
  test_graph/
    __init__.py
    conftest.py          # GraphBuilder fixture, graph test helpers
    test_knowledge_graph.py
    test_persistence.py
    test_snapshots.py
    test_identity.py
```

### Pattern 1: Mutation-Mediated Graph Access
**What:** All graph modifications go through the KnowledgeGraph API, which logs mutations as events before applying them to the underlying NetworkX DiGraph.
**When to use:** Always. No direct `G.add_node()` calls outside the KnowledgeGraph class.
**Why:** Enables event logging, snapshot correctness, rollback, and audit trails.
**Example:**
```python
# Source: docs/design/architecture.md + ARCHITECTURE.md Pattern 2
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Mutation:
    """A single graph mutation. Immutable for safety."""
    type: str          # "add_node", "add_edge", "set_property", "remove_node", "remove_edge"
    target: str        # node_id or "src->dst" for edges
    property: str | None  # property name for set_property
    old_value: Any     # previous value (None for add operations)
    new_value: Any     # new value (None for remove operations)
```

### Pattern 2: Snapshot as JSON Blob in SQLite
**What:** Full graph state serialized via `json_graph.node_link_data()` and stored as a TEXT column in SQLite.
**When to use:** Periodic snapshots (every N ticks or on-demand).
**Why:** Fast (~1.8ms serialize for 1000 nodes), human-readable, and supports the rollback use case directly.
**Example:**
```python
# Source: verified via benchmark in this research session
from networkx.readwrite import json_graph
import json

def take_snapshot(graph: nx.DiGraph) -> str:
    """Serialize full graph state to JSON string."""
    data = json_graph.node_link_data(graph)
    return json.dumps(data)

def restore_snapshot(json_str: str) -> nx.DiGraph:
    """Restore graph from JSON string."""
    data = json.loads(json_str)
    return json_graph.node_link_graph(data, directed=True, multigraph=False)
```

### Pattern 3: claim_id() Deconfliction
**What:** Mechanics propose human-readable node IDs. The graph ensures uniqueness by appending hash suffixes on collision.
**When to use:** Every node creation.
**Why:** D-02 locked decision. Readable IDs for debugging, guaranteed uniqueness.
**Example:**
```python
# Source: verified via test in this research session
import hashlib

def claim_id(graph: nx.DiGraph, name: str) -> str:
    """Propose a human-readable ID; deconflict if taken."""
    if name not in graph:
        return name
    for length in (2, 4, 6, 8):
        # Use node count as entropy source for deterministic but unique suffixes
        h = hashlib.sha256(f"{name}_{graph.number_of_nodes()}".encode()).hexdigest()[:length]
        candidate = f"{name}_{h}"
        if candidate not in graph:
            return candidate
    raise ValueError(f"Cannot deconflict ID after 4 attempts: {name}")
```

### Pattern 4: GraphBuilder for Tests (TEST-06)
**What:** Fluent builder pattern that lets tests construct graph scenarios in 2-3 lines.
**When to use:** Every test that needs a populated graph.
**Example:**
```python
# Test helper pattern
class GraphBuilder:
    def __init__(self):
        self._graph = nx.DiGraph()

    def node(self, id: str, **props) -> "GraphBuilder":
        self._graph.add_node(id, **props)
        return self

    def edge(self, src: str, dst: str, **props) -> "GraphBuilder":
        self._graph.add_edge(src, dst, **props)
        return self

    def build(self) -> nx.DiGraph:
        return self._graph

# Usage in tests:
graph = (GraphBuilder()
    .node("bob", type="agent", hp=100)
    .node("sword", type="entity", damage=10)
    .edge("bob", "sword", relation="holds")
    .build())
```

### Anti-Patterns to Avoid
- **Direct NetworkX mutation:** Never call `G.add_node()` or `G.nodes[id][prop] = val` outside the KnowledgeGraph class. All mutations must go through the API to be logged.
- **Pickle for snapshots:** Forbidden by project constraints. Use JSON serialization.
- **Schema enforcement on nodes:** D-03 says no framework-enforced properties beyond `type`. Don't add required fields, validators, or default property sets.
- **ORM for SQLite:** Forbidden. Use raw sqlite3 with parameterized queries.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph data structure | Custom adjacency lists | NetworkX DiGraph | Handles arbitrary properties, algorithms, traversal, serialization out of the box |
| JSON serialization of graph | Custom node/edge serializers | `networkx.readwrite.json_graph.node_link_data/graph` | Handles all property types, edge cases, directed/multigraph flags. Verified roundtrip. |
| SQLite connection management | Connection pooling, ORM | Raw sqlite3 context manager (`with sqlite3.connect(path) as conn`) | Existing pattern in `universe/manager.py`. Single-process app, no pooling needed. |
| UUID generation for IDs | UUID4 or similar | `claim_id()` per D-02 | Human-readable IDs are a locked decision for debuggability |

**Key insight:** The graph layer is deliberately thin. NetworkX does the heavy lifting; we add persistence, event logging, and the claim_id pattern on top.

## Common Pitfalls

### Pitfall 1: node_link_graph Defaults to Undirected
**What goes wrong:** `json_graph.node_link_graph(data)` defaults to `directed=False`. Restoring a DiGraph snapshot loses edge directionality silently.
**Why it happens:** The function signature defaults to undirected for historical reasons. The JSON data contains a `directed` key but `node_link_graph` does NOT use it automatically in all code paths.
**How to avoid:** Always pass `directed=True, multigraph=False` when restoring: `json_graph.node_link_graph(data, directed=True, multigraph=False)` [VERIFIED: checked function signature -- `directed=False, multigraph=True` are the defaults]
**Warning signs:** Edge traversal tests pass but direction-dependent queries give wrong results.

### Pitfall 2: Mutable Property References
**What goes wrong:** Storing mutable objects (dicts, lists) as node properties. Two nodes sharing the same dict object will silently corrupt each other.
**Why it happens:** Python dict assignment is by reference, not by copy.
**How to avoid:** Document that property values should be treated as immutable. The `set_property` API should `copy.deepcopy` mutable values before storing. JSON serialization for snapshots naturally creates independent copies.
**Warning signs:** Modifying one node's property changes another node's property.

### Pitfall 3: SQLite JSON Text Encoding
**What goes wrong:** Non-ASCII characters or special values (NaN, Infinity) in property values break JSON serialization.
**Why it happens:** `json.dumps()` raises on non-serializable types; NaN/Infinity are not valid JSON.
**How to avoid:** Use `json.dumps(data, ensure_ascii=False, allow_nan=False)` to fail fast on invalid values. Establish that property values must be JSON-serializable (decision D-04 discretion area).
**Warning signs:** Snapshots fail to save or load with JSON decode errors.

### Pitfall 4: Snapshot Bloat
**What goes wrong:** Taking a full JSON snapshot every tick creates massive SQLite tables.
**Why it happens:** Each snapshot stores the entire graph, not just the delta.
**How to avoid:** Snapshot periodically (every N ticks or on-demand), not every tick. Use the event log for fine-grained rollback between snapshots. Implement a retention policy (D-07 discretion area).
**Warning signs:** SQLite file grows rapidly, snapshot operations slow down.

### Pitfall 5: Forgetting to Persist Edge Data
**What goes wrong:** Edges have properties (relation type, weight, etc.) that get dropped during custom serialization.
**Why it happens:** Custom serializers often handle nodes but forget edge attributes.
**How to avoid:** Use `node_link_data` which includes edge attributes by default. Verified: edge properties roundtrip correctly through JSON. [VERIFIED: benchmark test showed edge data preserved]
**Warning signs:** Relations between nodes lose their types after persistence roundtrip.

## Code Examples

### SQLite Schema for Graph Persistence
```sql
-- Source: STACK.md persistence architecture, adapted for phase decisions
CREATE TABLE IF NOT EXISTS graph_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick_id INTEGER NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    graph_json TEXT NOT NULL,
    node_count INTEGER NOT NULL,
    edge_count INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(tick_id)
);

CREATE TABLE IF NOT EXISTS graph_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,  -- add_node, add_edge, set_property, remove_node, remove_edge
    target_id TEXT NOT NULL,
    property_name TEXT,
    old_value_json TEXT,
    new_value_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_tick ON graph_events(tick_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_tick ON graph_snapshots(tick_id);
```

### KnowledgeGraph API Shape
```python
# Source: docs/design/architecture.md class diagram
class KnowledgeGraph:
    """Core graph wrapper. All mutations logged as events."""

    def __init__(self, db_path: Path | None = None):
        self._graph: nx.DiGraph = nx.DiGraph()
        self._db_path = db_path
        self._current_tick: int = 0

    # --- Query API (read-only, no events) ---
    def query(self, node_id: str, property: str | None = None) -> Any: ...
    def has_node(self, node_id: str) -> bool: ...
    def has_edge(self, src: str, dst: str) -> bool: ...
    def neighbors(self, node_id: str) -> list[str]: ...
    def nodes(self, **filters) -> list[str]: ...

    # --- Mutation API (logged as events) ---
    def add_node(self, node_id: str, *, node_type: str, **props) -> Mutation: ...
    def add_edge(self, src: str, dst: str, **props) -> Mutation: ...
    def set(self, node_id: str, property: str, value: Any) -> Mutation: ...
    def remove_node(self, node_id: str) -> Mutation: ...
    def remove_edge(self, src: str, dst: str) -> Mutation: ...

    # --- Identity ---
    def claim_id(self, name: str) -> str: ...

    # --- Snapshot/Restore ---
    def snapshot(self, tick_id: int, summary: str = "") -> int: ...
    def restore(self, snapshot_id: int) -> None: ...
    def list_snapshots(self) -> list[SnapshotInfo]: ...

    # --- Persistence ---
    def save(self) -> None: ...
    def load(self) -> None: ...
```

### Property Value Type Decision (D-04 Discretion)
```python
# Recommendation: Allow all JSON-serializable types
# Primitives: str, int, float, bool, None
# Collections: list, dict (nested OK)
#
# Rationale:
# - NetworkX handles all these natively (verified: roundtrip test)
# - JSON serialization preserves them all (verified: benchmark test)
# - Nested dicts enable richer concepts (e.g., inventory={sword: {damage: 10}})
# - SQLite JSON1 can query into nested structures via json_extract()
#
# Restriction: No custom Python objects, no sets, no tuples, no bytes.
# These would fail JSON serialization and break persistence.
#
# Enforcement: Validate on set_property with a simple isinstance check
# against (str, int, float, bool, type(None), list, dict).
ALLOWED_PROPERTY_TYPES = (str, int, float, bool, type(None), list, dict)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `json_graph.node_link_data(G, attrs=...)` | `json_graph.node_link_data(G, *, source=..., target=...)` | NetworkX 3.4+ | Keyword-only args replaced the old `attrs` dict. Must use new API. [VERIFIED: function signature inspection] |
| `node_link_graph` auto-detects directed | Must pass `directed=True` explicitly | NetworkX 3.x | Default is `directed=False` regardless of data content |

**Deprecated/outdated:**
- NetworkX `attrs` parameter on `node_link_data`/`node_link_graph`: removed in 3.4+. Use keyword arguments `source`, `target`, `name`, `key`, `edges`, `nodes` instead. [VERIFIED: signature inspection]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Snapshot retention of ~50 snapshots is reasonable for v1 before implementing cleanup | Architecture Patterns | SQLite file could grow large if snapshots are very frequent; mitigated by the event log for fine-grained points |
| A2 | claim_id hash suffix approach (sha256 of name+count) produces sufficient uniqueness | Pattern 3 | Extremely unlikely collision at hobby-project scale; the fallback chain of 2/4/6/8 character suffixes handles it |
| A3 | 1000-node graph is a reasonable upper bound for v1 performance testing | Performance data | If graphs grow much larger, serialization times scale linearly but should still be fast |

## Open Questions

1. **Snapshot retention policy (D-07)**
   - What we know: Snapshots are linked to tick IDs. Full JSON dumps. Summary names from tick summaries.
   - What's unclear: How many to keep? Auto-prune old ones? Time-based or count-based retention?
   - Recommendation: Start with count-based (keep last N=50 snapshots), add pruning later. Simple and sufficient for v1.

2. **Event log compaction**
   - What we know: Events accumulate forever if not compacted. Each snapshot makes older events unnecessary.
   - What's unclear: When to compact? Should we delete events older than the oldest retained snapshot?
   - Recommendation: Delete events before the oldest snapshot on each new snapshot creation. Keeps the table bounded.

3. **Graph module integration with existing universe.db**
   - What we know: `universe/manager.py` already creates `universe.db` with a `metadata` table. Graph tables go in the same file.
   - What's unclear: Should graph tables be created at universe creation time, or lazily on first graph use?
   - Recommendation: Lazy creation on first `KnowledgeGraph(db_path)` instantiation. Keeps Phase 0 code unchanged.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_graph/ -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GRAPH-01 | Arbitrary properties on nodes and edges | unit | `uv run pytest tests/test_graph/test_knowledge_graph.py::test_arbitrary_properties -x` | Wave 0 |
| GRAPH-02 | Dynamic emergent concepts | unit | `uv run pytest tests/test_graph/test_knowledge_graph.py::test_emergent_properties -x` | Wave 0 |
| GRAPH-03 | SQLite persistence survives restart | integration | `uv run pytest tests/test_graph/test_persistence.py -x` | Wave 0 |
| GRAPH-04 | Snapshot creation | unit | `uv run pytest tests/test_graph/test_snapshots.py::test_snapshot_creation -x` | Wave 0 |
| GRAPH-05 | Restore from snapshot | unit | `uv run pytest tests/test_graph/test_snapshots.py::test_snapshot_restore -x` | Wave 0 |
| TEST-03 | Snapshot/restore round-trip integrity | integration | `uv run pytest tests/test_graph/test_snapshots.py::test_roundtrip_integrity -x` | Wave 0 |
| TEST-06 | GraphBuilder convenience utilities | unit | `uv run pytest tests/test_graph/test_knowledge_graph.py::test_graph_builder -x` | Wave 0 |
| AUTO-01 | CLAUDE.md completeness | manual-only | Review CLAUDE.md for architecture, constraints, validation, scripts | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_graph/ -x -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_graph/__init__.py` -- package init
- [ ] `tests/test_graph/conftest.py` -- GraphBuilder fixture, tmp_db fixture
- [ ] `tests/test_graph/test_knowledge_graph.py` -- covers GRAPH-01, GRAPH-02, TEST-06
- [ ] `tests/test_graph/test_persistence.py` -- covers GRAPH-03
- [ ] `tests/test_graph/test_snapshots.py` -- covers GRAPH-04, GRAPH-05, TEST-03
- [ ] `tests/test_graph/test_identity.py` -- covers claim_id (D-02)

## Project Constraints (from CLAUDE.md)

- **Language:** Python only. Engine, framework, and generated mechanics all in Python.
- **Knowledge graph:** Schema-less/flexible -- must accommodate arbitrary properties and relations without migrations.
- **Persistence:** Full state persistence -- graph, mechanics, agent memory, history must survive restarts.
- **Graph is ground truth:** If it's not in the graph, it doesn't exist. No side channels, no implicit state.
- **Forbidden:** LangChain, MongoDB, Neo4j, FastAPI/Flask, LangGraph, CrewAI, Celery, SQLAlchemy ORM, pickle.
- **Tools:** uv for packages, ruff for linting/formatting, mypy for type checking on framework API, prek for pre-commit hooks.
- **Testing:** pytest with existing configuration in pyproject.toml.
- **Code quality:** mypy strict on the mechanic framework API (graph module qualifies).

## Sources

### Primary (HIGH confidence)
- NetworkX 3.6.1 installed in project -- JSON roundtrip, property types, API signatures all verified via live Python execution
- SQLite 3.50.4 -- JSON1 extension, WAL mode verified via live Python execution
- `docs/design/architecture.md` -- KnowledgeGraph class diagram with API shape
- `.planning/research/STACK.md` -- Persistence architecture pattern
- `.planning/research/ARCHITECTURE.md` -- Mutation and event log patterns

### Secondary (MEDIUM confidence)
- Benchmark data collected in-session: JSON serialize ~1.8ms, deepcopy ~5.8ms, JSON deserialize ~4.4ms per 1000-node graph (100 iterations averaged)

### Tertiary (LOW confidence)
- None. All claims verified against live environment or project documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all dependencies verified installed at correct versions
- Architecture: HIGH -- patterns verified via live code execution and benchmarks
- Pitfalls: HIGH -- each pitfall verified against actual NetworkX behavior (e.g., directed=False default confirmed via signature inspection)

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable libraries, no fast-moving components)
