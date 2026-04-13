"""Tests for MECH17 degrade seed mechanic.

The use-on-tool form of degrade: actor swings/uses a held tool; tool's
``durability`` decrements by ``usage_cost`` (default 1). At/below 0 the
tool is removed (which drops its ``holds`` edge as a consequence).

UC-R05 routing note
-------------------
The Phase-3 manifest's classified verb is ``strike`` with ``target=dummy``
and ``instrument=sword``. The Phase-4 harness routes by ``verb`` -> mechanic
``id`` and ``target = classified.target or classified.indirect_object`` --
there is no ``instrument`` slot. The harness cannot route this UC to the
``degrade`` mechanic without a use-case rewrite. Combined with UC-R05's
threshold-flag assertion semantics (``broken=true`` on intact zero-durability
node) being a different shape than degrade-with-removal-at-zero, UC-R05's
``expected_outcome`` stays ``blocked`` (rationale documented in 04-10
SUMMARY). These tests therefore exercise the mechanic directly, not via the
harness.
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.degrade import DegradeMechanic


@pytest.fixture
def mechanic() -> DegradeMechanic:
    return DegradeMechanic()


@pytest.fixture
def held_sword_graph() -> KnowledgeGraph:
    """Alice holds a worn sword (durability=3)."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent")
    kg.add_node("yard", node_type="entity", subtype="room")
    kg.add_node("sword", node_type="entity", subtype="weapon", durability=3)
    kg.add_edge("alice", "yard", relation="located_in")
    kg.add_edge("alice", "sword", relation="holds")
    return kg


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestDegradeMetadata:
    def test_id(self, mechanic: DegradeMechanic) -> None:
        assert mechanic.id == "degrade"

    def test_voluntary(self, mechanic: DegradeMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: DegradeMechanic) -> None:
        for tag in ("resource", "durability"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestDegradeCheck:
    def test_passes_for_held_tool_with_durability(
        self, held_sword_graph: KnowledgeGraph, mechanic: DegradeMechanic
    ) -> None:
        ctx = MechanicContext(held_sword_graph, actor="alice", target="sword")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_actor_missing(self, mechanic: DegradeMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("sword", node_type="entity", durability=3)
        ctx = MechanicContext(kg, actor="alice", target="sword")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("actor" in r for r in result.reasons)

    def test_fails_when_target_missing(self, mechanic: DegradeMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("target" in r for r in result.reasons)

    def test_fails_when_target_not_held(self, mechanic: DegradeMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("sword", node_type="entity", durability=3)
        # No holds edge.
        ctx = MechanicContext(kg, actor="alice", target="sword")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("hold" in r for r in result.reasons)

    def test_fails_when_target_missing_durability(self, mechanic: DegradeMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("rock", node_type="entity")  # no durability
        kg.add_edge("alice", "rock", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="rock")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("durability" in r for r in result.reasons)

    def test_fails_when_durability_not_int(self, mechanic: DegradeMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("sword", node_type="entity", durability="three")  # str, not numeric
        kg.add_edge("alice", "sword", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("durability" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestDegradeApply:
    def test_decrements_durability_by_default_1(
        self, held_sword_graph: KnowledgeGraph, mechanic: DegradeMechanic
    ) -> None:
        ctx = MechanicContext(held_sword_graph, actor="alice", target="sword")
        mechanic.apply(ctx)
        assert held_sword_graph.query("sword").get("durability") == 2
        # Node + edge intact while above 0.
        assert held_sword_graph.has_node("sword")
        assert held_sword_graph.has_edge("alice", "sword")

    def test_decrements_by_usage_cost_when_provided(
        self, mechanic: DegradeMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("sword", node_type="entity", durability=10, usage_cost=3)
        kg.add_edge("alice", "sword", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        mechanic.apply(ctx)
        assert kg.query("sword").get("durability") == 7

    def test_removes_node_when_durability_reaches_zero(
        self, mechanic: DegradeMechanic
    ) -> None:
        """Last swing reduces durability to 0; node + holds edge are gone."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("sword", node_type="entity", durability=1)
        kg.add_edge("alice", "sword", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        mechanic.apply(ctx)
        assert not kg.has_node("sword")
        assert not kg.has_edge("alice", "sword")

    def test_removes_node_when_durability_goes_negative(
        self, mechanic: DegradeMechanic
    ) -> None:
        """A high usage_cost beyond durability still removes the tool."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("sword", node_type="entity", durability=2, usage_cost=5)
        kg.add_edge("alice", "sword", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        mechanic.apply(ctx)
        assert not kg.has_node("sword")
        assert not kg.has_edge("alice", "sword")

    def test_three_swings_match_uc_r05_durability_chain(
        self, held_sword_graph: KnowledgeGraph, mechanic: DegradeMechanic
    ) -> None:
        """Sequential apply mirrors UC-R05's intent: 3->2->1->gone."""
        ctx = MechanicContext(held_sword_graph, actor="alice", target="sword")
        mechanic.apply(ctx)
        assert held_sword_graph.query("sword").get("durability") == 2
        mechanic.apply(ctx)
        assert held_sword_graph.query("sword").get("durability") == 1
        mechanic.apply(ctx)
        # Third swing takes 1 -> 0; per PLAN.md degrade contract, removes.
        assert not held_sword_graph.has_node("sword")
        assert not held_sword_graph.has_edge("alice", "sword")

    def test_preserves_int_when_inputs_are_int(self, mechanic: DegradeMechanic) -> None:
        """durability stays an int when both inputs are int."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("sword", node_type="entity", durability=5, usage_cost=2)
        kg.add_edge("alice", "sword", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        mechanic.apply(ctx)
        new = kg.query("sword").get("durability")
        assert new == 3
        assert isinstance(new, int)
