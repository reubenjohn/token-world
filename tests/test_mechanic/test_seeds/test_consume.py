"""Tests for MECH15 consume seed mechanic."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.consume import ConsumeMechanic


@pytest.fixture
def mechanic() -> ConsumeMechanic:
    return ConsumeMechanic()


@pytest.fixture
def uc_r02_graph() -> KnowledgeGraph:
    """UC-R02 shape: hungry alice holding an apple."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", hunger=80)
    kg.add_node("kitchen", node_type="entity", subtype="room")
    kg.add_node("apple", node_type="entity", subtype="food", nutrition=25)
    kg.add_edge("alice", "kitchen", relation="located_in")
    kg.add_edge("alice", "apple", relation="holds")
    return kg


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestConsumeMetadata:
    def test_id(self, mechanic: ConsumeMechanic) -> None:
        assert mechanic.id == "consume"

    def test_voluntary(self, mechanic: ConsumeMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: ConsumeMechanic) -> None:
        for tag in ("object_interaction", "resource"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestConsumeCheck:
    def test_passes_for_held_food(
        self, uc_r02_graph: KnowledgeGraph, mechanic: ConsumeMechanic
    ) -> None:
        ctx = MechanicContext(uc_r02_graph, actor="alice", target="apple")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_target_not_held(self, mechanic: ConsumeMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", hunger=50)
        kg.add_node("apple", node_type="entity", subtype="food", nutrition=10)
        # No holds edge.
        ctx = MechanicContext(kg, actor="alice", target="apple")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("hold" in r for r in result.reasons)

    def test_fails_when_target_missing_nutrition(self, mechanic: ConsumeMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", hunger=50)
        kg.add_node("rock", node_type="entity", subtype="rock")  # no nutrition
        kg.add_edge("alice", "rock", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="rock")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("nutrition" in r for r in result.reasons)

    def test_fails_when_actor_missing_hunger(self, mechanic: ConsumeMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")  # no hunger
        kg.add_node("apple", node_type="entity", nutrition=10)
        kg.add_edge("alice", "apple", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="apple")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("hunger" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestConsumeApply:
    def test_uc_r02_happy_path(
        self, uc_r02_graph: KnowledgeGraph, mechanic: ConsumeMechanic
    ) -> None:
        """UC-R02: hunger 80 - nutrition 25 = 55; apple is gone."""
        ctx = MechanicContext(uc_r02_graph, actor="alice", target="apple")
        mechanic.apply(ctx)
        assert uc_r02_graph.query("alice").get("hunger") == 55
        assert not uc_r02_graph.has_node("apple")
        # edge dropped with the node
        assert not uc_r02_graph.has_edge("alice", "apple")

    def test_hunger_floors_at_zero(self, mechanic: ConsumeMechanic) -> None:
        """Nutrition greater than hunger clamps to 0, not negative."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", hunger=5)
        kg.add_node("feast", node_type="entity", nutrition=100)
        kg.add_edge("alice", "feast", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="feast")
        mechanic.apply(ctx)
        assert kg.query("alice").get("hunger") == 0
        assert not kg.has_node("feast")

    def test_preserves_int_when_inputs_are_int(self, mechanic: ConsumeMechanic) -> None:
        """hunger stays an int when both inputs are int."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", hunger=10)
        kg.add_node("nut", node_type="entity", nutrition=3)
        kg.add_edge("alice", "nut", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="nut")
        mechanic.apply(ctx)
        new_hunger = kg.query("alice").get("hunger")
        assert new_hunger == 7
        assert isinstance(new_hunger, int)
