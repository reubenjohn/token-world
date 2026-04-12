"""Tests for the movement seed mechanic."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.movement.mechanic import MovementMechanic


@pytest.fixture
def movement_graph() -> KnowledgeGraph:
    """Graph with two rooms connected by edges and an agent."""
    kg = KnowledgeGraph()
    kg.add_node("room_a", node_type="entity")
    kg.add_node("room_b", node_type="entity")
    kg.add_node("alice", node_type="agent", location="room_a")
    kg.add_edge("room_a", "room_b", relation="path")
    kg.add_edge("room_b", "room_a", relation="path")
    return kg


@pytest.fixture
def mechanic() -> MovementMechanic:
    return MovementMechanic()


class TestMovementCheck:
    def test_check_passes_with_valid_path(
        self, movement_graph: KnowledgeGraph, mechanic: MovementMechanic
    ) -> None:
        ctx = MechanicContext(movement_graph, actor="alice", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is True
        assert result.reasons == []

    def test_check_fails_no_location(
        self, movement_graph: KnowledgeGraph, mechanic: MovementMechanic
    ) -> None:
        movement_graph.add_node("bob", node_type="agent")
        ctx = MechanicContext(movement_graph, actor="bob", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("has no location" in r for r in result.reasons)

    def test_check_fails_no_path(
        self, movement_graph: KnowledgeGraph, mechanic: MovementMechanic
    ) -> None:
        movement_graph.remove_edge("room_a", "room_b")
        ctx = MechanicContext(movement_graph, actor="alice", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("No path" in r for r in result.reasons)

    def test_check_fails_target_missing(
        self, movement_graph: KnowledgeGraph, mechanic: MovementMechanic
    ) -> None:
        ctx = MechanicContext(movement_graph, actor="alice", target="room_c")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("does not exist" in r for r in result.reasons)

    def test_check_fails_actor_missing(self, mechanic: MovementMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("room_b", node_type="entity")
        ctx = MechanicContext(kg, actor="ghost", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("does not exist" in r for r in result.reasons)


class TestMovementApply:
    def test_apply_returns_location_mutation(
        self, movement_graph: KnowledgeGraph, mechanic: MovementMechanic
    ) -> None:
        ctx = MechanicContext(movement_graph, actor="alice", target="room_b")
        mutations = mechanic.apply(ctx)
        assert len(mutations) == 1
        m = mutations[0]
        assert m.type == "set_property"
        assert m.target == "alice"
        assert m.property == "location"
        assert m.new_value == "room_b"

    def test_apply_changes_graph_state(
        self, movement_graph: KnowledgeGraph, mechanic: MovementMechanic
    ) -> None:
        ctx = MechanicContext(movement_graph, actor="alice", target="room_b")
        mechanic.apply(ctx)
        assert ctx.query_node("alice", "location") == "room_b"


class TestMovementProperties:
    def test_is_voluntary(self, mechanic: MovementMechanic) -> None:
        assert mechanic.voluntary is True

    def test_id(self, mechanic: MovementMechanic) -> None:
        assert mechanic.id == "movement"

    def test_watches_returns_empty(self, mechanic: MovementMechanic) -> None:
        assert mechanic.watches() == []
