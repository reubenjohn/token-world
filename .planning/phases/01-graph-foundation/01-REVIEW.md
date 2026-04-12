---
phase: 01-graph-foundation
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - CLAUDE.md
  - src/token_world/graph/__init__.py
  - src/token_world/graph/events.py
  - src/token_world/graph/identity.py
  - src/token_world/graph/knowledge_graph.py
  - src/token_world/graph/models.py
  - src/token_world/graph/persistence.py
  - tests/test_graph/__init__.py
  - tests/test_graph/conftest.py
  - tests/test_graph/test_identity.py
  - tests/test_graph/test_knowledge_graph.py
  - tests/test_graph/test_persistence.py
  - tests/test_graph/test_snapshots.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Reviewed the complete graph foundation implementation: `KnowledgeGraph`, `GraphPersistence`, `EventStore`, `claim_id`, data models, and their test suites.

The overall design is solid. The event audit trail, property validation, snapshot/restore, and persistence are well-structured. The test suite has good coverage with clear naming and good fixture design.

Four warnings were found — all bugs or logic errors that will produce incorrect behavior under reachable conditions. No security vulnerabilities were found. Three info items cover minor quality concerns.

---

## Warnings

### WR-01: `add_edge()` silently creates typeless "ghost" nodes, bypassing all invariants

**File:** `src/token_world/graph/knowledge_graph.py:196`
**Issue:** `self._graph.add_edge(src, dst, **safe_props)` is a raw NetworkX call. If `src` or `dst` does not exist in the graph, NetworkX silently creates a bare node with no properties. The resulting node has no `type` field, violating the project's "only `agent` or `entity` nodes" invariant (CLAUDE.md critical constraint #3). This ghost node then appears in `kg.nodes()` but not in `kg.nodes(type="agent")` or `kg.nodes(type="entity")`, creating a split-brain between the full node list and type-filtered queries. Every event log entry, persistence roundtrip, and snapshot that follows will carry this corrupted state.

Verified by running:
```python
kg.add_node("a", node_type="agent")
kg.add_edge("a", "ghost_node")
kg.query("ghost_node")   # returns {} -- no "type" key
kg.nodes()               # returns ["a", "ghost_node"]
kg.nodes(type="agent")   # returns ["a"] -- ghost is invisible
```

**Fix:** Add explicit existence checks for both endpoints before delegating to NetworkX:
```python
def add_edge(self, src: str, dst: str, **props: Any) -> Mutation:
    if src not in self._graph:
        raise KeyError(f"Source node '{src}' does not exist")
    if dst not in self._graph:
        raise KeyError(f"Destination node '{dst}' does not exist")
    for v in props.values():
        _validate_value(v)
    ...
```

---

### WR-02: `add_node()` silently overwrites an existing node without raising an error

**File:** `src/token_world/graph/knowledge_graph.py:157`
**Issue:** `self._graph.add_node(node_id, type=node_type, **safe_props)` delegates to NetworkX which silently merges/overwrites properties when a node with the same `node_id` already exists. The operation still logs an `"add_node"` event, creating a misleading audit trail. A caller expecting to create a new node actually corrupts an existing one with no warning. This is especially dangerous in mechanic-generated code that calls `kg.add_node()` with an ID from `kg.claim_id()` — if the mechanic forgets to call `claim_id` first, it silently destroys an existing node's properties.

**Fix:** Raise `ValueError` if the node already exists:
```python
def add_node(self, node_id: str, *, node_type: str, **props: Any) -> Mutation:
    if node_id in self._graph:
        raise ValueError(f"Node '{node_id}' already exists. Use set() to update properties.")
    if node_type not in ("agent", "entity"):
        ...
```

---

### WR-03: `query()` returns live mutable references, allowing silent graph corruption

**File:** `src/token_world/graph/knowledge_graph.py:99-100`
**Issue:** Both overloads of `query()` return live references into the underlying NetworkX node attribute dict. Mutating the returned list or dict mutates the graph's stored state directly, bypassing validation, event logging, and the deep-copy invariant established by `_safe_copy`. This breaks the core "mutations only through API" guarantee. The same problem exists for `query("bob")` returning a shallow `dict()` copy — scalar values are copied, but mutable values (lists, dicts) inside remain live references.

Verified:
```python
inv = kg.query("bob", "inventory")   # returns ["sword"]
inv.append("potion")                  # mutates graph in-place, no event logged
kg.query("bob", "inventory")          # returns ["sword", "potion"] -- corrupted
```

**Fix:** Apply `_safe_copy` / `copy.deepcopy` to the return value. Since `query` is on the hot read path, only copy mutable types:
```python
def query(self, node_id: str, property: str | None = None) -> Any:
    if node_id not in self._graph:
        raise KeyError(f"Node '{node_id}' does not exist")
    if property is None:
        return {k: _safe_copy(v) for k, v in self._graph.nodes[node_id].items()}
    return _safe_copy(self._graph.nodes[node_id][property])
```

---

### WR-04: `claim_id()` hash is seeded by current node count — non-deterministic and collision-prone

**File:** `src/token_world/graph/identity.py:29`
**Issue:** The hash input is `f"{name}_{graph.number_of_nodes()}"`. The deconflicted ID produced for a given `name` depends on how many nodes are currently in the graph. Two calls to `claim_id("wallet")` with different graph sizes return different suffix strings. This means:
1. The mapping from a name to its deconflicted ID is non-reproducible.
2. If `graph.number_of_nodes()` happens to produce the same hash prefix as an existing node at length 2, the algorithm advances to length 4 — but the length-4 hash is also anchored to the same count, so it does not explore a different space. The deconfliction only avoids collisions by accident.
3. Re-importing a graph from a snapshot and then calling `claim_id("wallet")` again may return a *different* ID than was returned during the original run, breaking any stored cross-references that embed the deconflicted ID.

The architecture doc references `"wallet" -> "wallet_a7" -> "wallet_a7z6"` as the expected pattern; the current implementation does not guarantee this stable progression.

**Fix:** Seed the hash on the name and collision index only — not the current node count:
```python
def claim_id(graph: nx.DiGraph, name: str) -> str:
    if name not in graph:
        return name
    for attempt, length in enumerate((2, 4, 6, 8), start=1):
        h = hashlib.sha256(f"{name}_{attempt}".encode()).hexdigest()[:length]
        candidate = f"{name}_{h}"
        if candidate not in graph:
            return candidate
    raise ValueError(f"Cannot deconflict ID after 4 attempts: {name}")
```

This produces stable, reproducible IDs independent of graph size.

---

## Info

### IN-01: `remove_edge()` raises `NetworkXError` instead of `KeyError` on missing edge

**File:** `src/token_world/graph/knowledge_graph.py:303`
**Issue:** `remove_node()` explicitly validates existence and raises `KeyError`. `remove_edge()` does not validate and lets NetworkX raise `networkx.exception.NetworkXError` instead. This inconsistency forces callers to catch two different exception types for the same logical "target does not exist" scenario, and leaks an internal dependency into the public API contract.

**Fix:** Add an existence check that raises `KeyError` for consistency:
```python
def remove_edge(self, src: str, dst: str) -> Mutation:
    if not self._graph.has_edge(src, dst):
        raise KeyError(f"Edge '{src}->{dst}' does not exist")
    old_data = dict(self._graph.edges[src, dst])
    ...
```

---

### IN-02: Duplicate-tick snapshot silently invalidates stored `snapshot_id` references

**File:** `src/token_world/graph/persistence.py:193`
**Issue:** `graph_snapshots` has a `UNIQUE(tick_id)` constraint, and `save_snapshot()` uses `INSERT OR REPLACE`. If `snapshot(tick_id=5)` is called twice, SQLite deletes the first row and inserts a new one with a new `snapshot_id`. Any code that stored the old `snapshot_id` will get `ValueError: No snapshot with id N` on restore. The return value of the first `snapshot()` call becomes silently stale. No test covers this case.

**Fix:** Either raise an error when snapshotting a tick that already has a snapshot, or document and test the "replace" behavior explicitly so callers know not to cache `snapshot_id` values across multiple snapshots at the same tick.

---

### IN-03: `set()` cannot distinguish "property previously set to `None`" from "property did not exist"

**File:** `src/token_world/graph/knowledge_graph.py:236`
**Issue:** `old_value = self._graph.nodes[node_id].get(property)` returns `None` whether the property key is absent or its value is literally `None`. Consequently, `Mutation.old_value` and `GraphEvent.old_value_json` are both `None` in both cases, making it impossible to determine from the audit log whether a `set_property` event was a first-write or an update from `None`.

**Fix:** Use `_MISSING = object()` as a sentinel:
```python
_MISSING = object()

old_raw = self._graph.nodes[node_id].get(property, _MISSING)
old_value = None if old_raw is _MISSING else old_raw
old_value_json = None if old_raw is _MISSING else json.dumps(old_raw)
```

This preserves the `None` encoding for `json.dumps(None) = "null"` while distinguishing absent from null.

---

_Reviewed: 2026-04-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
