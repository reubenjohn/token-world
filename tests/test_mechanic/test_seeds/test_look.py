"""Tests for MECH02 look seed mechanic."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.look import LookMechanic


@pytest.fixture
def uc_s02_graph() -> KnowledgeGraph:
    """UC-S02 shape: alice in room_a, bob in room_b, wall between."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("bob", node_type="agent", position=[10, 0])
    kg.add_node("room_a", node_type="entity", subtype="room", bbox=[-5, -5, 5, 5])
    kg.add_node("room_b", node_type="entity", subtype="room", bbox=[5, -5, 15, 5])
    kg.add_node(
        "wall_1",
        node_type="entity",
        subtype="wall",
        bbox=[4.9, -5, 5.1, 5],
        occludes=True,
    )
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("bob", "room_b", relation="located_in")
    kg.add_edge("wall_1", "room_a", relation="borders")
    kg.add_edge("wall_1", "room_b", relation="borders")
    return kg


@pytest.fixture
def mechanic() -> LookMechanic:
    return LookMechanic()


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestLookMetadata:
    def test_id(self, mechanic: LookMechanic) -> None:
        assert mechanic.id == "look"

    def test_voluntary(self, mechanic: LookMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: LookMechanic) -> None:
        assert "spatial" in mechanic.tags
        assert "observation" in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestLookCheck:
    def test_passes_for_located_actor(
        self, uc_s02_graph: KnowledgeGraph, mechanic: LookMechanic
    ) -> None:
        ctx = MechanicContext(uc_s02_graph, actor="alice", target="bob")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_actor_missing(self, mechanic: LookMechanic) -> None:
        kg = KnowledgeGraph()
        ctx = MechanicContext(kg, actor="ghost", target="anyone")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("actor" in r for r in result.reasons)

    def test_fails_when_actor_has_no_location(self, mechanic: LookMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("located_in" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply() — UC-S02 invariants
# ---------------------------------------------------------------------------


class TestLookApply:
    def test_uc_s02_does_not_grant_saw_across_wall(
        self, uc_s02_graph: KnowledgeGraph, mechanic: LookMechanic
    ) -> None:
        """Core UC-S02 invariant: alice must NOT end up with `saw` set."""
        ctx = MechanicContext(uc_s02_graph, actor="alice", target="bob")
        muts = mechanic.apply(ctx)
        # No mutation should set `saw`.
        assert all(m.property != "saw" for m in muts if m.type == "set_property")
        props = uc_s02_graph.query("alice")
        assert "saw" not in props

    def test_uc_s02_bob_not_in_last_observed(
        self, uc_s02_graph: KnowledgeGraph, mechanic: LookMechanic
    ) -> None:
        """bob is in room_b, alice is in room_a — bob is NOT observed."""
        ctx = MechanicContext(uc_s02_graph, actor="alice", target="bob")
        mechanic.apply(ctx)
        observed = uc_s02_graph.query("alice").get("last_observed", [])
        assert "bob" not in observed

    def test_same_room_entities_are_observed(self, mechanic: LookMechanic) -> None:
        """An entity sharing alice's room IS in last_observed."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("room_a", node_type="entity", subtype="room")
        kg.add_node("lamp", node_type="entity", subtype="lamp")
        kg.add_edge("alice", "room_a", relation="located_in")
        kg.add_edge("lamp", "room_a", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="lamp")
        mechanic.apply(ctx)
        observed = kg.query("alice").get("last_observed", [])
        assert "lamp" in observed

    def test_occluders_are_filtered_from_last_observed(self, mechanic: LookMechanic) -> None:
        """Walls with occludes=True in the same room are NOT observed."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("room_a", node_type="entity", subtype="room")
        kg.add_node("wall_in_room", node_type="entity", subtype="wall", occludes=True)
        kg.add_edge("alice", "room_a", relation="located_in")
        kg.add_edge("wall_in_room", "room_a", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="wall_in_room")
        mechanic.apply(ctx)
        observed = kg.query("alice").get("last_observed", [])
        assert "wall_in_room" not in observed
