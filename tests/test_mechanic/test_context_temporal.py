"""ctx.temporal must be lazy and return a working TemporalIndex."""

from __future__ import annotations

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext


def test_ctx_temporal_lazy(tmp_path) -> None:
    """Building a context must not build the index — only first access does."""
    kg = KnowledgeGraph(db_path=tmp_path / "t.db")
    kg.add_node("a", node_type="entity")
    ctx = MechanicContext(kg, actor="a", target="a")
    assert ctx._temporal is None  # not yet built

    hist = ctx.temporal.query_history("a")
    assert any(e.event_type == "add_node" for e in hist)
    assert ctx._temporal is not None  # now cached


def test_ctx_temporal_cached(tmp_path) -> None:
    """Repeated accesses return the same TemporalIndex instance."""
    kg = KnowledgeGraph(db_path=tmp_path / "t.db")
    kg.add_node("x", node_type="entity")
    ctx = MechanicContext(kg, actor="x", target="x")
    assert ctx.temporal is ctx.temporal


def test_ctx_without_temporal_access_does_not_build(tmp_path) -> None:
    """Touching other DSL methods must not trigger temporal build."""
    kg = KnowledgeGraph(db_path=tmp_path / "t.db")
    kg.add_node("x", node_type="entity")
    ctx = MechanicContext(kg, actor="x", target="x")
    # Exercise some non-temporal DSL methods
    assert ctx.has_node("x") is True
    assert ctx.find_nodes(type="entity") == ["x"]
    assert ctx._temporal is None


def test_ctx_spatial_and_temporal_independent(tmp_path) -> None:
    """Accessing spatial must not build temporal, and vice versa."""
    kg = KnowledgeGraph(db_path=tmp_path / "t.db")
    kg.add_node("a", node_type="entity", position=[0.0, 0.0])
    ctx = MechanicContext(kg, actor="a", target="a")

    _ = ctx.spatial.nearest((0.0, 0.0), k=1)
    assert ctx._spatial is not None
    assert ctx._temporal is None

    _ = ctx.temporal.query_history("a")
    assert ctx._temporal is not None
