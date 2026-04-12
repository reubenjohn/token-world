"""ctx.spatial must be lazy and return a working SpatialIndex."""

from __future__ import annotations

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext


def test_ctx_spatial_is_lazy(tmp_path) -> None:
    """Building a context must not build the index — only first access does."""
    kg = KnowledgeGraph(db_path=tmp_path / "ctx.db")
    kg.add_node("alice", node_type="agent", position=[0.0, 0.0])
    ctx = MechanicContext(kg, actor="alice", target="alice")
    assert ctx._spatial is None  # not yet built

    hit = ctx.spatial.nearest((0.1, 0.1), k=1)
    assert hit == ["alice"]
    assert ctx._spatial is not None  # now cached


def test_ctx_spatial_caches_instance(tmp_path) -> None:
    """Repeated accesses return the same SpatialIndex instance."""
    kg = KnowledgeGraph(db_path=tmp_path / "ctx.db")
    kg.add_node("a", node_type="entity", position=[0.0, 0.0])
    ctx = MechanicContext(kg, actor="a", target="a")
    first = ctx.spatial
    second = ctx.spatial
    assert first is second


def test_ctx_without_spatial_access_does_not_build(tmp_path) -> None:
    """Touching other DSL methods must not trigger spatial build."""
    kg = KnowledgeGraph(db_path=tmp_path / "ctx.db")
    kg.add_node("x", node_type="entity")
    ctx = MechanicContext(kg, actor="x", target="x")
    # Exercise some non-spatial DSL methods
    assert ctx.has_node("x") is True
    assert ctx.has_node("missing") is False
    assert ctx.find_nodes(type="entity") == ["x"]
    # Index should still be unbuilt
    assert ctx._spatial is None
