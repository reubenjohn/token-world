---
phase: 03-design-validation
plan: 02
type: execute
wave: 1
depends_on: [01]
files_modified:
  - src/token_world/graph/spatial.py
  - src/token_world/mechanic/context.py
  - tests/test_graph/test_spatial_index.py
  - tests/test_mechanic/test_context_spatial.py
autonomous: true
requirements:
  - GRAPH-06
tags:
  - spatial
  - rtree
  - mechanic-context

must_haves:
  truths:
    - "A mechanic can call ctx.spatial.nearest((x, y), k=1) and get a list of node IDs sorted by distance"
    - "A mechanic can call ctx.spatial.within((minx, miny, maxx, maxy)) and get node IDs whose position or bbox intersects the region"
    - "Nodes without position/bbox are silently skipped — no errors, not indexed"
    - "Mechanics that never access ctx.spatial pay zero rtree cost (index is lazy per-context)"
    - "SpatialIndex can be rebuilt from graph state alone — never a parallel source of truth"
  artifacts:
    - path: "src/token_world/graph/spatial.py"
      provides: "SpatialIndex class with rebuild/nearest/within/intersects"
      exports: ["SpatialIndex"]
      min_lines: 80
    - path: "src/token_world/mechanic/context.py"
      provides: "MechanicContext.spatial lazy @property"
      contains: "def spatial"
    - path: "tests/test_mechanic/test_context_spatial.py"
      provides: "Tests that ctx.spatial is lazy and returns a SpatialIndex"
  key_links:
    - from: "src/token_world/mechanic/context.py"
      to: "src/token_world/graph/spatial.py"
      via: "lazy import inside @property to keep rtree out of the import graph for non-spatial mechanics"
      pattern: "from token_world.graph.spatial import SpatialIndex"
    - from: "src/token_world/graph/spatial.py"
      to: "rtree.index.Index"
      via: "internal rtree Index with int-id → node_id mapping dict"
      pattern: "from rtree"
---

<objective>
Deliver the optional R-tree spatial index primitive (GRAPH-06) as `SpatialIndex` in `src/token_world/graph/spatial.py`, exposed to mechanics via a lazy `MechanicContext.spatial` accessor.

Purpose: Enable mechanics that care about 2D proximity (movement, line-of-sight, area-of-effect) to query nearest-neighbor and bbox-intersection queries efficiently, without paying any cost when not used.

Output: A working `SpatialIndex`, a `spatial` property on `MechanicContext`, and green tests for all cases including missing-position safety and lazy-build.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/03-design-validation/03-CONTEXT.md
@.planning/phases/03-design-validation/03-RESEARCH.md
@src/token_world/graph/knowledge_graph.py
@src/token_world/graph/models.py
@src/token_world/mechanic/context.py
@tests/test_graph/conftest.py
@tests/test_graph/test_spatial_index.py

<interfaces>
Position conventions on graph nodes (JSON-safe lists; see Phase 1 ALLOWED_PROPERTY_TYPES):
- `position: [x, y]` — point (list[float] length 2)
- `bbox: [minx, miny, maxx, maxy]` — axis-aligned 2D bbox (list[float] length 4)
- If both present: `bbox` wins.
- Nodes with neither: not indexed (no error).

Target API (from RESEARCH.md §Spatial Index):
```python
class SpatialIndex:
    def __init__(self, graph: KnowledgeGraph) -> None: ...
    def rebuild(self) -> None: ...
    def nearest(self, point: tuple[float, float], *, k: int = 1,
                node_type: str | None = None,
                subtype: str | None = None) -> list[str]: ...
    def within(self, bbox: tuple[float, float, float, float], *,
               node_type: str | None = None,
               subtype: str | None = None) -> list[str]: ...
    def intersects(self, node_id: str, *,
                   node_type: str | None = None,
                   subtype: str | None = None) -> list[str]: ...
```

MechanicContext integration (lazy):
```python
@property
def spatial(self) -> SpatialIndex:
    if self._spatial is None:
        from token_world.graph.spatial import SpatialIndex
        self._spatial = SpatialIndex(self._graph)
        self._spatial.rebuild()
    return self._spatial
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement SpatialIndex (rtree-backed) with rebuild/nearest/within/intersects</name>
  <files>src/token_world/graph/spatial.py, tests/test_graph/test_spatial_index.py</files>
  <read_first>
    - .planning/phases/03-design-validation/03-RESEARCH.md §Spatial Index (GRAPH-06), §Code Examples (rtree usage)
    - src/token_world/graph/knowledge_graph.py (for `.nodes()` iteration and `.query(node_id)` to read position/bbox)
    - tests/test_graph/test_spatial_index.py (Wave 0 stubs — the contract)
    - tests/test_graph/conftest.py (for `kg` fixture and GraphBuilder)
  </read_first>
  <behavior>
    - nearest(point, k=1) returns k closest node_ids by Euclidean centroid distance.
    - within(bbox) returns node_ids whose point or bbox intersects the query bbox.
    - intersects(node_id) returns node_ids whose bbox overlaps node_id's bbox (excluding node_id itself). If node_id has no bbox/position, raises ValueError.
    - node_type / subtype kwargs filter results by the matching property on the node.
    - rebuild() is idempotent: calling twice on an unchanged graph yields the same index state.
    - Node without position/bbox is not indexed (no error, not returned).
    - Invalid position/bbox shape (wrong length, non-numeric) logs a warning via loguru and skips the node (do not crash — robustness for gap-analysis scenarios).
  </behavior>
  <action>
    Create `src/token_world/graph/spatial.py` implementing `SpatialIndex` per the RESEARCH.md contract.

    Key implementation notes:
    - `from rtree import index` — use `index.Index(properties=index.Property(dimension=2))`.
    - rtree requires **int IDs**; maintain `self._id_to_node: dict[int, str]` and `self._node_to_id: dict[str, int]`, allocating fresh ints on insert.
    - Point nodes: insert as zero-area bbox `(x, y, x, y)`.
    - bbox wins over position when both present (per research).
    - `rebuild()`: clear dicts, iterate `graph.nodes()` — for each, read props via `graph.query(node_id)`, extract position/bbox, validate, insert. Use `loguru.logger.warning(...)` for invalid shapes.
    - Reading nodes: use `for node_id in self._graph.nodes():` then `props = self._graph.query(node_id)`. Confirm these APIs exist by reading `knowledge_graph.py` — if `.nodes()` returns something other than an iterable of ids, adapt.
    - `nearest(point, k)`: call `self._rtree.nearest((x, y, x, y), k)`, translate ints back to node_ids, apply `node_type`/`subtype` filter. If rtree returns fewer than k, return what it has.
    - `within(bbox)`: call `self._rtree.intersection(bbox)`, filter, return.
    - `intersects(node_id)`: lookup node's bbox/position, call `within(...)`, remove node_id itself.
    - Module docstring must state: "Derived view over KnowledgeGraph; never a source of truth. Rebuildable from graph state alone."

    Also extend the Wave 0 spatial test file with edge-case tests:
    - `test_k_greater_than_node_count` — asks for k=10 when only 2 nodes, returns both without error.
    - `test_intersects_raises_for_positionless_node` — calling intersects on a node without position raises ValueError.
    - `test_rebuild_idempotent` — calling rebuild twice produces same query results.
    - `test_invalid_position_logged_and_skipped` — node with `position=["a", "b"]` is skipped, no exception raised. (Use caplog to assert the warning was emitted.)
    - `test_node_type_filter` — `nearest(point, k=5, node_type="agent")` only returns agent-typed nodes.
  </action>
  <verify>
    <automated>uv run pytest tests/test_graph/test_spatial_index.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "^class SpatialIndex" src/token_world/graph/spatial.py` passes
    - `grep -q "from rtree" src/token_world/graph/spatial.py` passes
    - `grep -q "def nearest\|def within\|def intersects\|def rebuild" src/token_world/graph/spatial.py` shows all 4 methods
    - `uv run pytest tests/test_graph/test_spatial_index.py -v` — all tests pass (no skips)
    - `uv run mypy src/token_world/graph/spatial.py` exits 0
    - Module docstring contains the word "derived" or "rebuildable" and references that the index is not a source of truth
  </acceptance_criteria>
  <done>SpatialIndex.nearest/within/intersects work on point and bbox nodes. Invalid shapes are logged+skipped. Filters work. All spatial tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire MechanicContext.spatial lazy property + regression test</name>
  <files>src/token_world/mechanic/context.py, tests/test_mechanic/test_context_spatial.py</files>
  <read_first>
    - src/token_world/mechanic/context.py (current state; identify where to add the property without breaking existing tests)
    - src/token_world/graph/spatial.py (Task 1 output)
    - tests/test_mechanic/ (existing structure for where to drop the test)
    - .planning/phases/03-design-validation/03-RESEARCH.md §Integration with existing MechanicContext DSL
  </read_first>
  <behavior>
    - `ctx.spatial` is a @property. On first access, it constructs a `SpatialIndex(self._graph)` and calls `.rebuild()`. Subsequent accesses return the cached instance.
    - A context that never accesses `ctx.spatial` does not trigger any rtree import or construction.
    - The `__init__` adds `self._spatial: SpatialIndex | None = None` without changing the existing signature.
  </behavior>
  <action>
    1. Edit `src/token_world/mechanic/context.py`:
       - Add `self._spatial: "SpatialIndex | None" = None` to `__init__` (use string annotation or `TYPE_CHECKING` import to avoid forcing rtree load at import time).
       - Add at the top: `from typing import TYPE_CHECKING` and `if TYPE_CHECKING: from token_world.graph.spatial import SpatialIndex`.
       - Add the property:
         ```python
         @property
         def spatial(self) -> "SpatialIndex":
             """Lazy R-tree spatial index over the graph. Built on first access."""
             if self._spatial is None:
                 from token_world.graph.spatial import SpatialIndex
                 self._spatial = SpatialIndex(self._graph)
                 self._spatial.rebuild()
             return self._spatial
         ```
    2. Create `tests/test_mechanic/test_context_spatial.py`:
       ```python
       """ctx.spatial must be lazy and return a working SpatialIndex."""
       from __future__ import annotations

       import sys

       import pytest

       from token_world.graph import KnowledgeGraph
       from token_world.mechanic.context import MechanicContext


       def test_ctx_spatial_is_lazy(tmp_path, monkeypatch) -> None:
           """Building a context must not import rtree or build the index."""
           # Ensure rtree isn't pre-imported from earlier tests in this session by checking
           # attribute presence, not module absence (rtree may legitimately be imported
           # elsewhere). Instead verify _spatial is None until access.
           kg = KnowledgeGraph(db_path=tmp_path / "ctx.db")
           kg.add_node("alice", node_type="agent", position=[0.0, 0.0])
           ctx = MechanicContext(kg, actor="alice", target="alice")
           assert ctx._spatial is None  # not yet built


           hit = ctx.spatial.nearest((0.1, 0.1), k=1)
           assert hit == ["alice"]
           assert ctx._spatial is not None  # now cached


       def test_ctx_spatial_caches_instance(tmp_path) -> None:
           kg = KnowledgeGraph(db_path=tmp_path / "ctx.db")
           kg.add_node("a", node_type="entity", position=[0.0, 0.0])
           ctx = MechanicContext(kg, actor="a", target="a")
           first = ctx.spatial
           second = ctx.spatial
           assert first is second


       def test_ctx_without_spatial_access_does_not_build(tmp_path) -> None:
           kg = KnowledgeGraph(db_path=tmp_path / "ctx.db")
           ctx = MechanicContext(kg, actor="x", target="x")
           # Touching other DSL methods must not trigger spatial build
           assert not ctx.has_node("x")
           assert ctx._spatial is None
       ```
    3. Verify existing mechanic tests still pass — no API breakage.
  </action>
  <verify>
    <automated>uv run pytest tests/test_mechanic/ -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def spatial" src/token_world/mechanic/context.py` passes
    - `grep -q "_spatial" src/token_world/mechanic/context.py` passes
    - `uv run pytest tests/test_mechanic/test_context_spatial.py -v` — all 3 tests pass
    - `uv run pytest tests/test_mechanic/ -v` — existing seed-mechanic tests still pass (no regressions)
    - `uv run mypy src/token_world/mechanic/context.py` exits 0
  </acceptance_criteria>
  <done>ctx.spatial is a working lazy accessor. Existing mechanic tests unchanged. Three new regression tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| mechanic → graph | Mechanics call ctx.spatial with arbitrary floats; graph nodes may contain malformed position/bbox properties (author error, not adversarial input). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-04 | DoS | SpatialIndex.rebuild on large graphs | accept | Bounded by graph size we control. 10k node rebuild measured <50ms on commodity hardware (RESEARCH.md A1). Not an attacker-controlled input. |
| T-03-05 | Tampering | Malformed `position` / `bbox` values on nodes | mitigate | `rebuild()` validates shape (length 2 or 4, numeric) and calls `loguru.logger.warning` + skips node; does not crash. Tested in `test_invalid_position_logged_and_skipped`. |
| T-03-06 | Info disclosure | None — index is read-only projection of already-accessible graph state | accept | No data crosses a trust boundary. |
</threat_model>

<verification>
- `uv run pytest tests/test_graph/test_spatial_index.py tests/test_mechanic/test_context_spatial.py -v` is green
- `uv run mypy src/token_world/graph/ src/token_world/mechanic/context.py` is green
- `uv run ruff check src/` is green
- No regressions in Phase 2 mechanic tests
</verification>

<success_criteria>
1. A mechanic that adds two nodes with `position=[0,0]` and `position=[10,10]` gets `["node_a"]` from `ctx.spatial.nearest((0.1, 0.1), k=1)`.
2. A mechanic that calls `ctx.spatial.within((-1,-1,1,1))` gets only nodes whose point/bbox intersects that box.
3. A mechanic that never touches `ctx.spatial` sees `ctx._spatial is None` throughout its lifetime.
4. Nodes with malformed position are skipped with a logged warning.
5. `ctx.spatial` is cached — two accesses return the same instance.
</success_criteria>

<output>
After completion, create `.planning/phases/03-design-validation/03-02-SUMMARY.md` listing: spatial.py artifact, MechanicContext.spatial accessor, test counts, and any design deviations from RESEARCH.md.
</output>
