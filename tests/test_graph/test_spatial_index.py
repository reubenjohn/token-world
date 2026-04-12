"""Stubs for GRAPH-06 SpatialIndex (Wave 1 will implement)."""

from __future__ import annotations

import pytest

spatial = pytest.importorskip("token_world.graph.spatial")


def test_nearest_returns_closest_point(kg) -> None:
    kg.add_node("a", node_type="entity", position=[0.0, 0.0])
    kg.add_node("b", node_type="entity", position=[10.0, 10.0])
    idx = spatial.SpatialIndex(kg)
    idx.rebuild()
    assert idx.nearest((0.1, 0.1), k=1) == ["a"]


def test_within_bbox_filters_correctly(kg) -> None:
    kg.add_node("a", node_type="entity", position=[1.0, 1.0])
    kg.add_node("b", node_type="entity", position=[50.0, 50.0])
    idx = spatial.SpatialIndex(kg)
    idx.rebuild()
    assert idx.within((0.0, 0.0, 5.0, 5.0)) == ["a"]


def test_missing_position_is_not_indexed(kg) -> None:
    kg.add_node("has_pos", node_type="entity", position=[0.0, 0.0])
    kg.add_node("no_pos", node_type="entity")  # intentionally no position
    idx = spatial.SpatialIndex(kg)
    idx.rebuild()
    # Querying a huge bbox should return only the one with position
    assert idx.within((-1000.0, -1000.0, 1000.0, 1000.0)) == ["has_pos"]


def test_bbox_node_intersects(kg) -> None:
    kg.add_node("room", node_type="entity", bbox=[0.0, 0.0, 10.0, 10.0])
    kg.add_node("table", node_type="entity", position=[5.0, 5.0])
    idx = spatial.SpatialIndex(kg)
    idx.rebuild()
    hits = idx.within((4.0, 4.0, 6.0, 6.0))
    assert "table" in hits
    assert "room" in hits  # bbox overlaps query region


def test_lazy_access_on_mechanic_context(kg) -> None:
    """ctx.spatial must be a @property that builds on first access only."""
    from token_world.mechanic.context import MechanicContext

    kg.add_node("alice", node_type="agent", position=[0.0, 0.0])
    ctx = MechanicContext(kg, actor="alice", target="alice")
    # Access should succeed and return something with .nearest
    assert hasattr(ctx.spatial, "nearest")
