"""Tests for GRAPH-06 SpatialIndex (Wave 1 implementation)."""

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


# --- Wave 1 edge-case tests ---


def test_k_greater_than_node_count(kg) -> None:
    """nearest with k larger than index size returns all indexed nodes."""
    kg.add_node("a", node_type="entity", position=[0.0, 0.0])
    kg.add_node("b", node_type="entity", position=[1.0, 1.0])
    idx = spatial.SpatialIndex(kg)
    idx.rebuild()
    hits = idx.nearest((0.0, 0.0), k=10)
    assert set(hits) == {"a", "b"}
    assert len(hits) == 2


def test_intersects_raises_for_positionless_node(kg) -> None:
    """intersects on a node with neither position nor bbox raises ValueError."""
    kg.add_node("ghost", node_type="entity")  # no position or bbox
    idx = spatial.SpatialIndex(kg)
    idx.rebuild()
    with pytest.raises(ValueError):
        idx.intersects("ghost")


def test_rebuild_idempotent(kg) -> None:
    """Calling rebuild twice produces the same query results."""
    kg.add_node("a", node_type="entity", position=[0.0, 0.0])
    kg.add_node("b", node_type="entity", position=[10.0, 10.0])
    idx = spatial.SpatialIndex(kg)
    idx.rebuild()
    first = idx.nearest((0.1, 0.1), k=2)
    idx.rebuild()
    second = idx.nearest((0.1, 0.1), k=2)
    assert first == second


def test_invalid_position_logged_and_skipped(kg, caplog) -> None:
    """Node with malformed position is logged as warning and skipped (no crash)."""
    # We need loguru messages to propagate to caplog. loguru does not route to
    # stdlib logging by default; add a handler that forwards to logging.
    import logging

    from loguru import logger

    class PropagateHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - glue
            logging.getLogger(record.name).handle(record)

    handler_id = logger.add(PropagateHandler(), format="{message}", level="WARNING")
    try:
        kg.add_node("bad", node_type="entity", position=["a", "b"])
        kg.add_node("good", node_type="entity", position=[0.0, 0.0])
        idx = spatial.SpatialIndex(kg)
        with caplog.at_level("WARNING"):
            idx.rebuild()  # must not raise
        # 'bad' is not indexed
        assert idx.within((-100.0, -100.0, 100.0, 100.0)) == ["good"]
        # Warning was emitted (loguru -> logging propagate)
        assert any(
            "bad" in rec.message or "position" in rec.message.lower() for rec in caplog.records
        )
    finally:
        logger.remove(handler_id)


def test_node_type_filter(kg) -> None:
    """nearest/within honor node_type filter."""
    kg.add_node("alice", node_type="agent", position=[0.0, 0.0])
    kg.add_node("rock", node_type="entity", position=[0.1, 0.1])
    kg.add_node("bob", node_type="agent", position=[5.0, 5.0])
    idx = spatial.SpatialIndex(kg)
    idx.rebuild()
    hits = idx.nearest((0.0, 0.0), k=5, node_type="agent")
    assert set(hits) == {"alice", "bob"}
    # rock excluded
    assert "rock" not in hits


def test_subtype_filter(kg) -> None:
    """nearest/within honor subtype filter."""
    kg.add_node("door1", node_type="entity", position=[0.0, 0.0], subtype="doorway")
    kg.add_node("chair", node_type="entity", position=[0.1, 0.1], subtype="furniture")
    kg.add_node("door2", node_type="entity", position=[5.0, 5.0], subtype="doorway")
    idx = spatial.SpatialIndex(kg)
    idx.rebuild()
    hits = idx.nearest((0.0, 0.0), k=5, subtype="doorway")
    assert set(hits) == {"door1", "door2"}
    assert "chair" not in hits


def test_intersects_excludes_self(kg) -> None:
    """intersects returns other overlapping nodes but not the query node itself."""
    kg.add_node("room_a", node_type="entity", bbox=[0.0, 0.0, 10.0, 10.0])
    kg.add_node("room_b", node_type="entity", bbox=[5.0, 5.0, 15.0, 15.0])
    idx = spatial.SpatialIndex(kg)
    idx.rebuild()
    hits = idx.intersects("room_a")
    assert "room_b" in hits
    assert "room_a" not in hits
