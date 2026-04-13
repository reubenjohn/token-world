"""Tests for MECH16 pickup seed mechanic + _count_holds helper."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds._helpers import _count_holds, _refuse_with_narrative
from token_world.mechanic.seeds.pickup import PickupMechanic


@pytest.fixture
def mechanic() -> PickupMechanic:
    return PickupMechanic()


@pytest.fixture
def uc_r04_graph() -> KnowledgeGraph:
    """UC-R04 shape: alice at inventory cap, item_10 on the floor."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", inventory_cap=10)
    kg.add_node("storeroom", node_type="entity", subtype="room")
    kg.add_edge("alice", "storeroom", relation="located_in")
    for i in range(10):
        item_id = f"item_{i:02d}"
        kg.add_node(item_id, node_type="entity", subtype="junk")
        kg.add_edge("alice", item_id, relation="holds")
    kg.add_node("item_10", node_type="entity", subtype="junk")
    kg.add_edge("item_10", "storeroom", relation="located_in")
    return kg


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestPickupMetadata:
    def test_id(self, mechanic: PickupMechanic) -> None:
        assert mechanic.id == "pickup"

    def test_voluntary(self, mechanic: PickupMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: PickupMechanic) -> None:
        for tag in ("object_interaction", "inventory"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# Shared helpers (_count_holds + _refuse_with_narrative)
# ---------------------------------------------------------------------------


class TestCountHolds:
    def test_zero_when_no_edges(self) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        assert _count_holds(ctx, "alice") == 0

    def test_counts_only_holds_edges(self) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("room", node_type="entity", subtype="room")
        kg.add_node("sword", node_type="entity")
        kg.add_node("shield", node_type="entity")
        kg.add_edge("alice", "room", relation="located_in")  # not holds
        kg.add_edge("alice", "sword", relation="holds")
        kg.add_edge("alice", "shield", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        assert _count_holds(ctx, "alice") == 2

    def test_ignores_incoming_holds(self) -> None:
        """held_by (reverse direction) must not be counted as holds."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("sword", node_type="entity")
        kg.add_edge("sword", "alice", relation="held_by")  # reverse
        ctx = MechanicContext(kg, actor="alice", target="sword")
        assert _count_holds(ctx, "alice") == 0


class TestRefuseWithNarrative:
    def test_writes_narrative_only(self) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        muts = _refuse_with_narrative(ctx, "alice", "no reason")
        assert len(muts) == 1
        assert kg.query("alice").get("last_refusal_narrative") == "no reason"
        assert "last_refusal_target" not in kg.query("alice")

    def test_writes_narrative_and_target(self) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("apple", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="apple")
        muts = _refuse_with_narrative(ctx, "alice", "cant", target="apple")
        assert len(muts) == 2
        props = kg.query("alice")
        assert props.get("last_refusal_narrative") == "cant"
        assert props.get("last_refusal_target") == "apple"


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestPickupCheck:
    def test_passes_with_cap_and_target(self, mechanic: PickupMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", inventory_cap=5)
        kg.add_node("coin", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="coin")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_target_missing(self, mechanic: PickupMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", inventory_cap=5)
        kg.add_node("placeholder", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="ghost")
        # has_node("ghost") is False — build a ctx whose target id is unknown
        # by pointing at a present node first then swapping.
        ctx.target = "ghost"
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("target" in r for r in result.reasons)

    def test_fails_when_actor_missing_cap(self, mechanic: PickupMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")  # no inventory_cap
        kg.add_node("coin", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="coin")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("inventory_cap" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply() — happy path, full, already-held
# ---------------------------------------------------------------------------


class TestPickupApply:
    def test_happy_path_adds_holds_edge(self, mechanic: PickupMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", inventory_cap=2)
        kg.add_node("coin", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="coin")
        mechanic.apply(ctx)
        assert kg.has_edge("alice", "coin")
        assert "coin" in ctx.neighbors("alice", relation="holds")

    def test_under_cap_from_count_one(self, mechanic: PickupMechanic) -> None:
        """Actor holds 1 of 5 — pickup succeeds, count becomes 2."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", inventory_cap=5)
        kg.add_node("sword", node_type="entity")
        kg.add_node("shield", node_type="entity")
        kg.add_edge("alice", "sword", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="shield")
        mechanic.apply(ctx)
        assert kg.has_edge("alice", "shield")
        assert len(ctx.neighbors("alice", relation="holds")) == 2

    def test_uc_r04_full_inventory_refuses(
        self, uc_r04_graph: KnowledgeGraph, mechanic: PickupMechanic
    ) -> None:
        """UC-R04: at cap → narrative, no edge, item stays on floor."""
        ctx = MechanicContext(uc_r04_graph, actor="alice", target="item_10")
        mechanic.apply(ctx)
        # No holds edge alice→item_10.
        assert not uc_r04_graph.has_edge("alice", "item_10")
        # item_10 still on the floor.
        assert uc_r04_graph.has_edge("item_10", "storeroom")
        # Refusal narrative recorded.
        alice_props = uc_r04_graph.query("alice")
        assert alice_props.get("last_refusal_narrative") == "inventory is full"
        assert alice_props.get("last_refusal_target") == "item_10"
        # inventory_cap unchanged.
        assert alice_props.get("inventory_cap") == 10

    def test_already_holding_refuses(self, mechanic: PickupMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", inventory_cap=5)
        kg.add_node("sword", node_type="entity")
        kg.add_edge("alice", "sword", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        mechanic.apply(ctx)
        # Still exactly one holds edge.
        assert len(ctx.neighbors("alice", relation="holds")) == 1
        assert kg.query("alice").get("last_refusal_narrative") == "already holding it"
