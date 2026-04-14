"""Tests for MECH01 passage_move seed mechanic and _find_open_passage helper."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds._helpers import _find_open_passage
from token_world.mechanic.seeds.passage_move import PassageMoveMechanic

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def doorway_graph() -> KnowledgeGraph:
    """Two rooms connected via an open doorway passage entity (UC-S01 shape)."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node("room_b", node_type="entity", subtype="room", bbox=[5, -5, 15, 5])
    kg.add_node(
        "doorway_1",
        node_type="entity",
        subtype="doorway",
        position=[5, 0],
        open=True,
    )
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("room_a", "doorway_1", relation="connects")
    kg.add_edge("doorway_1", "room_b", relation="connects")
    return kg


@pytest.fixture
def mechanic() -> PassageMoveMechanic:
    return PassageMoveMechanic()


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestPassageMoveMetadata:
    def test_id(self, mechanic: PassageMoveMechanic) -> None:
        assert mechanic.id == "passage_move"

    def test_voluntary(self, mechanic: PassageMoveMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: PassageMoveMechanic) -> None:
        assert "spatial" in mechanic.tags
        assert "passage" in mechanic.tags


# ---------------------------------------------------------------------------
# _find_open_passage helper
# ---------------------------------------------------------------------------


class TestFindOpenPassage:
    def test_finds_open_doorway(self, doorway_graph: KnowledgeGraph) -> None:
        ctx = MechanicContext(doorway_graph, actor="alice", target="room_b")
        assert _find_open_passage(ctx, "room_a", "room_b") == "doorway_1"

    def test_returns_none_when_doorway_closed(self, doorway_graph: KnowledgeGraph) -> None:
        doorway_graph.set("doorway_1", "open", False)
        ctx = MechanicContext(doorway_graph, actor="alice", target="room_b")
        assert _find_open_passage(ctx, "room_a", "room_b") is None

    def test_returns_none_when_no_passage_entity(self) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("room_a", node_type="entity")
        kg.add_node("room_b", node_type="entity")
        kg.add_edge("alice", "room_a", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="room_b")
        assert _find_open_passage(ctx, "room_a", "room_b") is None

    def test_accepts_bridge_subtype(self) -> None:
        """Bridges count as passages when traversable=True (UC-S06)."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("room_a", node_type="entity", subtype="room")
        kg.add_node("room_b", node_type="entity", subtype="room")
        kg.add_node(
            "bridge_stone",
            node_type="entity",
            subtype="bridge",
            traversable=True,
        )
        kg.add_edge("bridge_stone", "room_a", relation="connects")
        kg.add_edge("bridge_stone", "room_b", relation="connects")
        # bridge needs edges emanating FROM src for the walk; re-add in canonical direction
        kg.add_edge("room_a", "bridge_stone", relation="connects")
        ctx = MechanicContext(kg, actor="alice", target="room_b")
        # _find_open_passage walks src's connects neighbors; bridge must be among them.
        assert _find_open_passage(ctx, "room_a", "room_b") == "bridge_stone"


# ---------------------------------------------------------------------------
# passage_move.check()
# ---------------------------------------------------------------------------


class TestPassageMoveCheck:
    def test_check_succeeds_when_open_passage_exists(
        self, doorway_graph: KnowledgeGraph, mechanic: PassageMoveMechanic
    ) -> None:
        ctx = MechanicContext(doorway_graph, actor="alice", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is True, f"expected pass, got reasons={result.reasons}"

    def test_check_fails_when_passage_closed(
        self, doorway_graph: KnowledgeGraph, mechanic: PassageMoveMechanic
    ) -> None:
        doorway_graph.set("doorway_1", "open", False)
        ctx = MechanicContext(doorway_graph, actor="alice", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("no open passage" in r.lower() for r in result.reasons)

    def test_check_fails_when_no_passage(self, mechanic: PassageMoveMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("room_a", node_type="entity")
        kg.add_node("room_b", node_type="entity")
        kg.add_edge("alice", "room_a", relation="located_in")
        # No edge room_a→room_b at all.
        ctx = MechanicContext(kg, actor="alice", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("passage" in r.lower() for r in result.reasons)

    def test_check_fails_when_actor_missing_location(self, mechanic: PassageMoveMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("room_b", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("location" in r.lower() for r in result.reasons)

    def test_check_fails_when_actor_missing(self, mechanic: PassageMoveMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("room_b", node_type="entity")
        ctx = MechanicContext(kg, actor="ghost", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("does not exist" in r.lower() for r in result.reasons)

    def test_check_fails_when_target_missing(
        self, doorway_graph: KnowledgeGraph, mechanic: PassageMoveMechanic
    ) -> None:
        ctx = MechanicContext(doorway_graph, actor="alice", target="nowhere")
        result = mechanic.check(ctx)
        assert result.passed is False

    def test_check_succeeds_for_direct_connects(self, mechanic: PassageMoveMechanic) -> None:
        """UC-S07 shape: direct connects edge, no intermediate passage entity."""
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
        ctx = MechanicContext(kg, actor="alice", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is True, (
            f"direct connects should be accepted by passage_move; got {result.reasons}"
        )


# ---------------------------------------------------------------------------
# passage_move.apply()
# ---------------------------------------------------------------------------


class TestPassageMoveApply:
    def test_apply_moves_actor_through_doorway(
        self, doorway_graph: KnowledgeGraph, mechanic: PassageMoveMechanic
    ) -> None:
        ctx = MechanicContext(doorway_graph, actor="alice", target="room_b")
        mutations = mechanic.apply(ctx)
        # Post-state: alice located_in room_b, not in room_a.
        assert doorway_graph.has_edge("alice", "room_b")
        # and the edge carries the located_in relation
        edge_data = dict(doorway_graph._graph["alice"]["room_b"])
        assert edge_data.get("relation") == "located_in"
        assert not doorway_graph.has_edge("alice", "room_a")
        # At least two mutations (remove old + add new); may also set location prop.
        assert len(mutations) >= 2

    def test_apply_sets_location_property(
        self, doorway_graph: KnowledgeGraph, mechanic: PassageMoveMechanic
    ) -> None:
        """UC-S07 asserts alice.location == 'room_b' as a property_equals."""
        ctx = MechanicContext(doorway_graph, actor="alice", target="room_b")
        mechanic.apply(ctx)
        assert doorway_graph.query("alice", "location") == "room_b"

    def test_apply_direct_connects(self, mechanic: PassageMoveMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("room_a", node_type="entity", subtype="room")
        kg.add_node("room_b", node_type="entity", subtype="room")
        kg.add_edge("alice", "room_a", relation="located_in")
        kg.add_edge("room_a", "room_b", relation="connects")
        ctx = MechanicContext(kg, actor="alice", target="room_b")
        mechanic.apply(ctx)
        assert kg.has_edge("alice", "room_b")
        assert not kg.has_edge("alice", "room_a")
