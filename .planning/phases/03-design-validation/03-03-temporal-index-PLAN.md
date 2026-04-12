---
phase: 03-design-validation
plan: 03
type: execute
wave: 1
depends_on: [01]
files_modified:
  - src/token_world/graph/temporal.py
  - src/token_world/graph/persistence.py
  - src/token_world/mechanic/context.py
  - tests/test_graph/test_temporal_index.py
  - tests/test_mechanic/test_context_temporal.py
autonomous: true
requirements:
  - GRAPH-07
tags:
  - temporal
  - event-sourcing
  - mechanic-context

must_haves:
  truths:
    - "A mechanic can call ctx.temporal.query_history(node_id) and get all events targeting that node"
    - "A mechanic can call ctx.temporal.query_changes(property_name) and get all set_property events for that property"
    - "find_state_at_tick reconstructs a node's property dict as of the end of a given tick_id"
    - "Querying state before the oldest retained snapshot raises TemporalQueryOutOfRange"
    - "Mechanics that never access ctx.temporal pay zero query cost (lazy)"
    - "No new storage: temporal queries run against EventStore (session) + graph_events SQLite table (persistent)"
  artifacts:
    - path: "src/token_world/graph/temporal.py"
      provides: "TemporalIndex facade + TemporalQueryOutOfRange exception"
      exports: ["TemporalIndex", "TemporalQueryOutOfRange"]
      min_lines: 100
    - path: "src/token_world/graph/persistence.py"
      provides: "Two new CREATE INDEX IF NOT EXISTS on graph_events (target_id+tick, property_name+tick)"
      contains: "idx_events_target"
    - path: "src/token_world/mechanic/context.py"
      provides: "MechanicContext.temporal lazy @property"
      contains: "def temporal"
  key_links:
    - from: "src/token_world/graph/temporal.py"
      to: "src/token_world/graph/events.py (EventStore)"
      via: "session events pulled via graph._events.get_events()"
      pattern: "EventStore\\|_events"
    - from: "src/token_world/graph/temporal.py"
      to: "sqlite3 graph_events table"
      via: "parameterized queries with ? placeholders"
      pattern: "execute.*SELECT.*graph_events"
    - from: "src/token_world/graph/temporal.py"
      to: "snapshot retention policy"
      via: "find_state_at_tick consults oldest snapshot tick; raises OutOfRange past it"
      pattern: "TemporalQueryOutOfRange"
---

<objective>
Deliver the optional temporal index primitive (GRAPH-07) as `TemporalIndex` in `src/token_world/graph/temporal.py` — a read-only query facade over the existing `EventStore` (in-memory session events) plus the persisted `graph_events` SQLite table. Adds two SQLite indexes on `graph_events`. No new storage schema.

Purpose: Enable mechanics that care about history (e.g., "has this property changed in the last 10 ticks?", "what was the agent's hp at tick 42?") without inventing a parallel time-series store.

Output: Working `TemporalIndex`, lazy `MechanicContext.temporal` accessor, two SQLite indexes via `CREATE INDEX IF NOT EXISTS`, and green tests including the out-of-range guard.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/03-design-validation/03-CONTEXT.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@src/token_world/graph/knowledge_graph.py
@src/token_world/graph/events.py
@src/token_world/graph/persistence.py
@src/token_world/mechanic/context.py
@tests/test_graph/test_temporal_index.py

<interfaces>
From src/token_world/graph/events.py:
```python
@dataclass(frozen=True)
class GraphEvent:
    tick_id: int
    event_type: str          # add_node | add_edge | set_property | remove_node | remove_edge
    target_id: str
    property_name: str | None
    old_value_json: str | None
    new_value_json: str | None

class EventStore:
    def get_events(self, tick_id: int | None = None) -> list[GraphEvent]: ...
```

Existing SQLite schema (src/token_world/graph/persistence.py):
```sql
CREATE TABLE graph_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    property_name TEXT,
    old_value_json TEXT,
    new_value_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_tick ON graph_events(tick_id);   -- already present
-- NEW indexes to add in this plan:
CREATE INDEX IF NOT EXISTS idx_events_target ON graph_events(target_id, tick_id);
CREATE INDEX IF NOT EXISTS idx_events_property ON graph_events(property_name, tick_id);
```

Target API (from RESEARCH.md §Temporal Index):
```python
class TemporalQueryOutOfRange(Exception):
    """Raised when find_state_at_tick asks for a tick before the oldest retained snapshot."""

class TemporalIndex:
    def __init__(self, graph: KnowledgeGraph) -> None: ...
    def query_history(self, node_id: str, *,
                      tick_range: tuple[int, int] | None = None) -> list[GraphEvent]: ...
    def query_changes(self, property_name: str, *,
                      tick_range: tuple[int, int] | None = None,
                      node_id: str | None = None) -> list[GraphEvent]: ...
    def find_state_at_tick(self, node_id: str, tick_id: int) -> dict[str, Any]: ...
    def last_change(self, node_id: str, property_name: str) -> GraphEvent | None: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add SQLite indexes on graph_events (target_id, property_name)</name>
  <files>src/token_world/graph/persistence.py</files>
  <read_first>
    - src/token_world/graph/persistence.py (identify the `_ensure_tables` method and the executescript block)
    - tests/test_graph/ (any existing persistence tests, to confirm index additions don't break them)
  </read_first>
  <behavior>
    - After `_ensure_tables` runs, the `graph_events` table has three indexes: `idx_events_tick` (already present), `idx_events_target` on `(target_id, tick_id)`, and `idx_events_property` on `(property_name, tick_id)`.
    - The additions are idempotent (`IF NOT EXISTS`) and safe on existing databases.
  </behavior>
  <action>
    Edit `src/token_world/graph/persistence.py` `_ensure_tables` method — inside the `conn.executescript(...)` string, after the existing `CREATE INDEX IF NOT EXISTS idx_events_tick ON graph_events(tick_id);` line, add:
    ```sql
    CREATE INDEX IF NOT EXISTS idx_events_target ON graph_events(target_id, tick_id);
    CREATE INDEX IF NOT EXISTS idx_events_property ON graph_events(property_name, tick_id);
    ```
    That's the entire change. No other code or test edits required for this task — Task 2 will add the tests that exercise them.
  </action>
  <verify>
    <automated>uv run python -c "
    import sqlite3, tempfile, pathlib
    from token_world.graph import KnowledgeGraph
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / 'x.db'
        kg = KnowledgeGraph(db_path=p)
        kg.add_node('a', node_type='entity')
        kg.save()
        with sqlite3.connect(str(p)) as c:
            idx = [r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='graph_events'\").fetchall()]
            assert 'idx_events_target' in idx, idx
            assert 'idx_events_property' in idx, idx
            print('ok', idx)
    "</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "idx_events_target" src/token_world/graph/persistence.py` passes
    - `grep -q "idx_events_property" src/token_world/graph/persistence.py` passes
    - After creating any graph with persistence and saving, `sqlite_master` lists both new indexes on `graph_events`
    - `uv run pytest tests/test_graph/ -x -q` still green (no persistence regressions)
  </acceptance_criteria>
  <done>Two new indexes exist on graph_events; idempotent; existing tests unaffected.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement TemporalIndex + TemporalQueryOutOfRange; make Wave 0 temporal tests pass</name>
  <files>src/token_world/graph/temporal.py, tests/test_graph/test_temporal_index.py</files>
  <read_first>
    - src/token_world/graph/events.py (GraphEvent, EventStore — the authoritative shape)
    - src/token_world/graph/knowledge_graph.py (locate: how events are appended, how to reach in-memory events from a KnowledgeGraph instance, how snapshots tie to tick IDs)
    - src/token_world/graph/persistence.py (to learn the exact column names of graph_events and graph_snapshots)
    - src/token_world/graph/models.py (SnapshotInfo shape)
    - tests/test_graph/test_temporal_index.py (Wave 0 stubs — the acceptance contract)
    - .planning/phases/03-design-validation/03-RESEARCH.md §Temporal Index (GRAPH-07)
  </read_first>
  <behavior>
    - `query_history(node_id)` returns a list[GraphEvent] where each event has `target_id == node_id`. In tick order.
    - `query_history(node_id, tick_range=(lo, hi))` filters to events with `lo <= tick_id <= hi` (inclusive).
    - `query_changes("hp")` returns all `set_property` events with `property_name == "hp"`. Supports `node_id=` and `tick_range=`.
    - `find_state_at_tick(node_id, tick)` reconstructs node properties as of end of `tick`. Finds most recent snapshot at or before `tick`, loads node properties from snapshot, replays `set_property` / `remove_property` events between snapshot tick and `tick` (exclusive of later events).
    - `find_state_at_tick(node_id, tick)` raises `TemporalQueryOutOfRange` when no snapshot exists at or before `tick` AND the node's `add_node` event is not within reachable history (i.e., the event log has been compacted past it).
    - `last_change(node_id, property_name)` returns the most recent `set_property` GraphEvent for the pair, or `None`.
    - Queries combine in-memory events (`graph._events.get_events()`) with persisted events (via sqlite3). When no `db_path` is attached to the graph, only the in-memory store is consulted.
    - All SQLite queries use parameterized `?` placeholders (threat T-03-03 mitigation).
  </behavior>
  <action>
    1. Create `src/token_world/graph/temporal.py`:
       ```python
       """Temporal query facade over EventStore + graph_events SQLite table.

       Read-only. Derived view — never a source of truth. Queries combine
       the in-memory session EventStore with persisted events so mechanics
       can reason about history that predates the current process.
       """
       from __future__ import annotations

       import json
       import sqlite3
       from typing import TYPE_CHECKING, Any

       from token_world.graph.events import GraphEvent

       if TYPE_CHECKING:
           from token_world.graph.knowledge_graph import KnowledgeGraph


       class TemporalQueryOutOfRange(Exception):
           """Raised when a temporal query asks for state before the oldest retained snapshot."""


       class TemporalIndex:
           """Read-only temporal query facade.

           Combines in-memory EventStore (this session) with the persisted
           graph_events SQLite table (prior sessions). No new storage.
           """

           def __init__(self, graph: "KnowledgeGraph") -> None:
               self._graph = graph

           def query_history(
               self,
               node_id: str,
               *,
               tick_range: tuple[int, int] | None = None,
           ) -> list[GraphEvent]:
               """All events targeting node_id, in tick order.

               tick_range is inclusive on both ends.
               """
               mem = [e for e in self._graph._events.get_events()
                      if e.target_id == node_id]
               disk = self._query_disk(
                   "target_id = ?",
                   (node_id,),
                   tick_range=tick_range,
               )
               merged = self._merge(mem, disk)
               if tick_range is not None:
                   lo, hi = tick_range
                   merged = [e for e in merged if lo <= e.tick_id <= hi]
               return merged

           def query_changes(
               self,
               property_name: str,
               *,
               tick_range: tuple[int, int] | None = None,
               node_id: str | None = None,
           ) -> list[GraphEvent]:
               """All set_property events for the given property, in tick order."""
               mem = [
                   e for e in self._graph._events.get_events()
                   if e.event_type == "set_property"
                   and e.property_name == property_name
                   and (node_id is None or e.target_id == node_id)
               ]
               where = "event_type = 'set_property' AND property_name = ?"
               params: tuple[Any, ...] = (property_name,)
               if node_id is not None:
                   where += " AND target_id = ?"
                   params = (*params, node_id)
               disk = self._query_disk(where, params, tick_range=tick_range)
               merged = self._merge(mem, disk)
               if tick_range is not None:
                   lo, hi = tick_range
                   merged = [e for e in merged if lo <= e.tick_id <= hi]
               return merged

           def last_change(
               self, node_id: str, property_name: str
           ) -> GraphEvent | None:
               events = self.query_changes(property_name, node_id=node_id)
               return events[-1] if events else None

           def find_state_at_tick(
               self, node_id: str, tick_id: int
           ) -> dict[str, Any]:
               """Reconstruct node_id's property dict as of end of tick_id.

               Strategy:
                 1. Find most recent snapshot at or before tick_id.
                 2. If none and the add_node event is also out of reach, raise.
                 3. Replay set_property / remove_property events from snapshot tick
                    (exclusive) up through tick_id (inclusive).
               """
               if tick_id < 0:
                   raise TemporalQueryOutOfRange(
                       f"tick_id must be non-negative, got {tick_id}"
                   )

               base_state, base_tick = self._load_baseline(node_id, tick_id)
               # Replay events in (base_tick, tick_id]
               history = self.query_history(
                   node_id, tick_range=(base_tick + 1, tick_id)
               )
               state = dict(base_state)
               for e in history:
                   if e.event_type == "set_property" and e.property_name:
                       state[e.property_name] = (
                           json.loads(e.new_value_json)
                           if e.new_value_json is not None
                           else None
                       )
                   elif e.event_type == "remove_node":
                       state = {}
               return state

           # --- internals ---

           def _load_baseline(
               self, node_id: str, tick_id: int
           ) -> tuple[dict[str, Any], int]:
               """Return (state_dict, base_tick) for node_id as of some tick <= tick_id."""
               db_path = getattr(self._graph, "_db_path", None)
               if db_path is None:
                   # In-memory only. Baseline is the state just after add_node.
                   add_event = self._first_add_event(node_id)
                   if add_event is None or add_event.tick_id > tick_id:
                       raise TemporalQueryOutOfRange(
                           f"node {node_id!r} did not exist at tick {tick_id}"
                       )
                   return ({}, add_event.tick_id - 1)

               with sqlite3.connect(str(db_path)) as conn:
                   # Find most recent snapshot with tick_id <= target
                   row = conn.execute(
                       "SELECT tick_id, graph_json FROM graph_snapshots "
                       "WHERE tick_id <= ? ORDER BY tick_id DESC LIMIT 1",
                       (tick_id,),
                   ).fetchone()
                   if row is not None:
                       base_tick, graph_json = row
                       from networkx.readwrite import json_graph
                       data = json.loads(graph_json)
                       G = json_graph.node_link_graph(data, directed=True)
                       if not G.has_node(node_id):
                           # Node didn't exist in this snapshot; look for add_node
                           # between base_tick and tick_id
                           add = self._first_add_event(
                               node_id, tick_upper=tick_id
                           )
                           if add is None:
                               raise TemporalQueryOutOfRange(
                                   f"node {node_id!r} not in snapshot at tick "
                                   f"{base_tick} and no add_node found up to {tick_id}"
                               )
                           return ({}, add.tick_id - 1)
                       props = dict(G.nodes[node_id])
                       # Strip framework-internal keys if any (none known today)
                       return (props, base_tick)

               # No snapshot at or before tick_id — check if add_node is in reach
               add_event = self._first_add_event(node_id, tick_upper=tick_id)
               if add_event is None:
                   raise TemporalQueryOutOfRange(
                       f"no snapshot at or before tick {tick_id} and no "
                       f"add_node event for {node_id!r} is retained"
                   )
               return ({}, add_event.tick_id - 1)

           def _first_add_event(
               self, node_id: str, tick_upper: int | None = None
           ) -> GraphEvent | None:
               candidates = [
                   e for e in self.query_history(node_id)
                   if e.event_type == "add_node"
               ]
               if tick_upper is not None:
                   candidates = [e for e in candidates if e.tick_id <= tick_upper]
               return candidates[0] if candidates else None

           def _query_disk(
               self,
               where: str,
               params: tuple[Any, ...],
               *,
               tick_range: tuple[int, int] | None,
           ) -> list[GraphEvent]:
               db_path = getattr(self._graph, "_db_path", None)
               if db_path is None:
                   return []
               sql = (
                   "SELECT tick_id, event_type, target_id, property_name, "
                   "old_value_json, new_value_json "
                   "FROM graph_events WHERE " + where
               )
               full_params: tuple[Any, ...] = params
               if tick_range is not None:
                   sql += " AND tick_id BETWEEN ? AND ?"
                   full_params = (*params, tick_range[0], tick_range[1])
               sql += " ORDER BY tick_id ASC, event_id ASC"
               with sqlite3.connect(str(db_path)) as conn:
                   rows = conn.execute(sql, full_params).fetchall()
               return [
                   GraphEvent(
                       tick_id=r[0],
                       event_type=r[1],
                       target_id=r[2],
                       property_name=r[3],
                       old_value_json=r[4],
                       new_value_json=r[5],
                   )
                   for r in rows
               ]

           @staticmethod
           def _merge(
               mem: list[GraphEvent], disk: list[GraphEvent]
           ) -> list[GraphEvent]:
               seen = {(e.tick_id, e.event_type, e.target_id, e.property_name,
                        e.new_value_json) for e in disk}
               extra = [e for e in mem if (e.tick_id, e.event_type, e.target_id,
                                           e.property_name, e.new_value_json)
                        not in seen]
               return sorted(disk + extra, key=lambda e: e.tick_id)
       ```

       **Note on coupling:** the `_db_path` attribute access is internal (per Phase 1 encapsulation). Confirm it exists on KnowledgeGraph (it does, per `__init__`). If Phase 1 later exposes a public accessor, migrate; for now use the internal attribute — document with a comment.

    2. Extend the Wave 0 `tests/test_graph/test_temporal_index.py` with a few more tests:
       - `test_query_changes_node_id_filter` — setting "hp" on two different nodes, `query_changes("hp", node_id="a")` returns only `a`'s events.
       - `test_last_change_returns_none_when_absent` — `last_change("ghost", "whatever")` returns None.
       - `test_find_state_at_tick_uses_snapshot` — take a snapshot at tick 2 after adding a node with hp=100, set hp=50 at tick 3, `find_state_at_tick("a", 2)` → hp=100.
       - `test_query_history_merges_mem_and_disk` — set property, save, reopen graph from the same db_path, set another property, `query_history` returns both.
       - `test_parameterized_queries_no_injection` — call `query_history("alice'; DROP TABLE graph_events; --")` — must not raise, returns `[]`, graph_events table still exists.
  </action>
  <verify>
    <automated>uv run pytest tests/test_graph/test_temporal_index.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "^class TemporalIndex" src/token_world/graph/temporal.py` passes
    - `grep -q "^class TemporalQueryOutOfRange" src/token_world/graph/temporal.py` passes
    - `grep -q "ORDER BY tick_id" src/token_world/graph/temporal.py` passes (ordering guarantee)
    - `grep -q "execute(sql, full_params)" src/token_world/graph/temporal.py` passes (parameterized queries only)
    - `grep -nE "f[\"'].*\{.*\}.*SELECT|f[\"'].*\{.*\}.*FROM" src/token_world/graph/temporal.py` returns nothing (no f-string SQL — injection defense)
    - `uv run pytest tests/test_graph/test_temporal_index.py -v` all tests pass
    - `uv run mypy src/token_world/graph/temporal.py` exits 0
  </acceptance_criteria>
  <done>TemporalIndex.query_history, query_changes, find_state_at_tick, last_change all work. Out-of-range raises. Parameterized queries only. All temporal tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Wire MechanicContext.temporal lazy property + regression test</name>
  <files>src/token_world/mechanic/context.py, tests/test_mechanic/test_context_temporal.py</files>
  <read_first>
    - src/token_world/mechanic/context.py (note state from plan 02 — spatial property may already be added if plan 02 ran first; or may need to add alongside)
    - src/token_world/graph/temporal.py (Task 2 output)
    - tests/test_mechanic/ (existing structure)
  </read_first>
  <behavior>
    - `ctx.temporal` is a @property. On first access, it constructs `TemporalIndex(self._graph)`. Subsequent accesses return cached instance.
    - Does not import `temporal` module at `context.py` import time (lazy inside the property body).
    - Co-exists with `ctx.spatial` from plan 02 — both may be accessed independently.
  </behavior>
  <action>
    1. Edit `src/token_world/mechanic/context.py`:
       - Under the `TYPE_CHECKING` block, add `from token_world.graph.temporal import TemporalIndex`.
       - Add `self._temporal: "TemporalIndex | None" = None` in `__init__`.
       - Add:
         ```python
         @property
         def temporal(self) -> "TemporalIndex":
             """Lazy temporal query facade over graph event log."""
             if self._temporal is None:
                 from token_world.graph.temporal import TemporalIndex
                 self._temporal = TemporalIndex(self._graph)
             return self._temporal
         ```
    2. Create `tests/test_mechanic/test_context_temporal.py`:
       ```python
       """ctx.temporal must be lazy and return a working TemporalIndex."""
       from __future__ import annotations

       from token_world.graph import KnowledgeGraph
       from token_world.mechanic.context import MechanicContext


       def test_ctx_temporal_lazy(tmp_path) -> None:
           kg = KnowledgeGraph(db_path=tmp_path / "t.db")
           kg.add_node("a", node_type="entity")
           ctx = MechanicContext(kg, actor="a", target="a")
           assert ctx._temporal is None
           hist = ctx.temporal.query_history("a")
           assert any(e.event_type == "add_node" for e in hist)
           assert ctx._temporal is not None


       def test_ctx_temporal_cached(tmp_path) -> None:
           kg = KnowledgeGraph(db_path=tmp_path / "t.db")
           ctx = MechanicContext(kg, actor="x", target="x")
           assert ctx.temporal is ctx.temporal


       def test_ctx_without_temporal_access_does_not_build(tmp_path) -> None:
           kg = KnowledgeGraph(db_path=tmp_path / "t.db")
           ctx = MechanicContext(kg, actor="x", target="x")
           _ = ctx.has_node("x")
           assert ctx._temporal is None
       ```

    **Coordination with plan 02:** If this task lands before plan 02's task 2, just add the temporal property alongside the future spatial slot (placeholder `_spatial = None` harmless). If plan 02 lands first, augment the existing `__init__` rather than overwriting. Executor should read current file and add missing pieces idempotently — these are additive.
  </action>
  <verify>
    <automated>uv run pytest tests/test_mechanic/ -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def temporal" src/token_world/mechanic/context.py` passes
    - `uv run pytest tests/test_mechanic/test_context_temporal.py -v` passes
    - `uv run pytest tests/test_mechanic/ -v` — no regressions
    - `uv run mypy src/token_world/mechanic/context.py` exits 0
  </acceptance_criteria>
  <done>ctx.temporal is a working lazy accessor. Existing tests still pass. Three new tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| mechanic → SQLite | `node_id`, `property_name`, `tick_range` flow from mechanic code into sqlite3 queries. Project rule: parameterized queries only. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-03 | Injection | SQLite queries in `TemporalIndex._query_disk` | mitigate | All SQL uses `?` placeholders with tuple params (`conn.execute(sql, params)`); `where` fragments are static strings. Test `test_parameterized_queries_no_injection` asserts this. Acceptance criterion greps for any f-string SQL and fails. |
| T-03-07 | Info disclosure | Events may expose prior-session state to a mechanic | accept | Event log is internal project state. Mechanics already have full graph read access (Phase 2). Same trust level. |
| T-03-08 | DoS | Large event log scan on big SQLite DBs | mitigate | New indexes on `(target_id, tick_id)` and `(property_name, tick_id)` (Task 1) make the hot query paths O(log n). 100k-event DBs should resolve in milliseconds. |
</threat_model>

<verification>
- `uv run pytest tests/test_graph/test_temporal_index.py tests/test_mechanic/test_context_temporal.py -v` is green
- `uv run mypy src/token_world/graph/temporal.py src/token_world/graph/persistence.py src/token_world/mechanic/context.py` is green
- `uv run ruff check src/` is green
- No regressions in Phase 1/2 tests
</verification>

<success_criteria>
1. After adding node + setting property, `ctx.temporal.query_history("a")` returns both events in tick order.
2. After a snapshot at tick 5 with hp=100 and a set at tick 7 to hp=50, `ctx.temporal.find_state_at_tick("a", 5)` returns `{"hp": 100, ...}`.
3. Asking for state far before any retained snapshot raises `TemporalQueryOutOfRange`.
4. All SQL queries use `?` placeholders; no f-string SQL anywhere in the module.
5. Mechanics that never touch `ctx.temporal` never construct the TemporalIndex object.
</success_criteria>

<output>
After completion, create `.planning/phases/03-design-validation/03-03-SUMMARY.md` — list artifacts, note the two new SQLite indexes, describe the in-memory+disk merge strategy.
</output>
