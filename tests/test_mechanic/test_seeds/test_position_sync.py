"""Tests for MECH06 position_sync seed mechanic (involuntary post-move hook)."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.engine import ChainExecutionEngine
from token_world.mechanic.matchers import EdgeMatcher
from token_world.mechanic.seeds.passage_move import PassageMoveMechanic
from token_world.mechanic.seeds.position_sync import PositionSyncMechanic


# ---------------------------------------------------------------------------
# Metadata + matcher contract
# ---------------------------------------------------------------------------


class TestPositionSyncMetadata:
    def test_id(self) -> None:
        assert PositionSyncMechanic().id == "position_sync"

    def test_is_involuntary(self) -> None:
        assert PositionSyncMechanic().voluntary is False

    def test_tags(self) -> None:
        tags = PositionSyncMechanic().tags
        assert "spatial" in tags
        assert "post-move" in tags

    def test_watches_returns_located_in_edge_matcher(self) -> None:
        watchers = PositionSyncMechanic().watches()
        assert len(watchers) >= 1
        edge_watchers = [w for w in watchers if isinstance(w, EdgeMatcher)]
        assert any(
            w.event_type == "add_edge" and w.edge_label == "located_in"
            for w in edge_watchers
        )


# ---------------------------------------------------------------------------
# Direct apply behavior
# ---------------------------------------------------------------------------


class TestPositionSyncApply:
    def test_centroid_from_bbox(self) -> None:
        """When destination has a bbox, position_sync sets actor.position = centroid."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", position=[0, 0])
        kg.add_node("room_b", node_type="entity", bbox=[-5, -5, 5, 5])
        kg.add_edge("alice", "room_b", relation="located_in")
        # Chain ctx convention: target == actor (the one being moved).
        ctx = MechanicContext(kg, actor="alice", target="alice")
        mech = PositionSyncMechanic()
        check = mech.check(ctx)
        assert check.passed is True, f"expected pass, got {check.reasons}"
        mech.apply(ctx)
        assert kg.query("alice", "position") == [0, 0]

    def test_centroid_from_explicit_centroid_prop(self) -> None:
        """Destination with explicit centroid wins over bbox computation."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", position=[0, 0])
        kg.add_node(
            "room_b",
            node_type="entity",
            bbox=[5, -5, 15, 5],
            centroid=[10, 0],
        )
        kg.add_edge("alice", "room_b", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        mech = PositionSyncMechanic()
        assert mech.check(ctx).passed is True
        mech.apply(ctx)
        assert kg.query("alice", "position") == [10, 0]

    def test_copies_point_position(self) -> None:
        """If destination only has a point `position` (no bbox), copy that."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", position=[0, 0])
        kg.add_node("beacon", node_type="entity", position=[10, 3])
        kg.add_edge("alice", "beacon", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        mech = PositionSyncMechanic()
        assert mech.check(ctx).passed is True
        mech.apply(ctx)
        assert kg.query("alice", "position") == [10, 3]

    def test_skips_when_destination_has_no_spatial_data(self) -> None:
        """No bbox, no centroid, no position → check returns False (no-op, not error)."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", position=[0, 0])
        kg.add_node("void", node_type="entity")  # no spatial props
        kg.add_edge("alice", "void", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        mech = PositionSyncMechanic()
        result = mech.check(ctx)
        assert result.passed is False
        # alice.position untouched.
        assert kg.query("alice", "position") == [0, 0]


# ---------------------------------------------------------------------------
# Chain integration with passage_move
# ---------------------------------------------------------------------------


class TestPositionSyncChainIntegration:
    def test_chain_fires_after_passage_move(self) -> None:
        """End-to-end: passage_move adds located_in edge → position_sync fires → alice.position updated."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", position=[0, 0])
        kg.add_node(
            "room_a",
            node_type="entity",
            subtype="room",
            bbox=[-5, -5, 5, 5],
            centroid=[0, 0],
        )
        kg.add_node(
            "room_b",
            node_type="entity",
            subtype="room",
            bbox=[5, -5, 15, 5],
            centroid=[10, 0],
        )
        kg.add_edge("alice", "room_a", relation="located_in")
        kg.add_edge("room_a", "room_b", relation="connects")
        engine = ChainExecutionEngine(
            involuntary_mechanics=[PositionSyncMechanic()], max_depth=10
        )
        ctx = MechanicContext(kg, actor="alice", target="room_b")
        trace = engine.execute(PassageMoveMechanic(), ctx)
        assert trace.root.check_result.passed is True
        # Some involuntary fired (position_sync).
        assert trace.total_mechanics_executed >= 2
        # alice.position picked up room_b's centroid.
        assert kg.query("alice", "position") == [10, 0]
