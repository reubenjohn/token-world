"""Tests for MECH07 trade seed mechanic (single-tick atomic swap)."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.trade import TradeMechanic


@pytest.fixture
def mechanic() -> TradeMechanic:
    return TradeMechanic()


@pytest.fixture
def uc_o01_graph() -> KnowledgeGraph:
    """UC-O01 single-tick shape: both parties pre-staged with complementary offers."""
    kg = KnowledgeGraph()
    kg.add_node(
        "alice",
        node_type="agent",
        pending_trade={
            "offer_item": "sword",
            "demand_item": "coin_pouch",
            "counterparty": "bob",
        },
    )
    kg.add_node(
        "bob",
        node_type="agent",
        pending_trade={
            "offer_item": "coin_pouch",
            "demand_item": "sword",
            "counterparty": "alice",
        },
    )
    kg.add_node("sword", node_type="entity", subtype="weapon")
    kg.add_node("coin_pouch", node_type="entity", subtype="currency")
    kg.add_edge("alice", "sword", relation="holds")
    kg.add_edge("bob", "coin_pouch", relation="holds")
    return kg


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestTradeMetadata:
    def test_id(self, mechanic: TradeMechanic) -> None:
        assert mechanic.id == "trade"

    def test_voluntary(self, mechanic: TradeMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: TradeMechanic) -> None:
        for tag in ("social", "trade"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestTradeCheck:
    def test_passes_for_two_party_pending(
        self, uc_o01_graph: KnowledgeGraph, mechanic: TradeMechanic
    ) -> None:
        ctx = MechanicContext(uc_o01_graph, actor="alice", target="bob")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_counterparty_missing_pending(
        self, mechanic: TradeMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            pending_trade={"offer_item": "a", "demand_item": "b", "counterparty": "bob"},
        )
        kg.add_node("bob", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="bob")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("counterparty" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestTradeApply:
    def test_uc_o01_happy_path_swaps_atomically(
        self, uc_o01_graph: KnowledgeGraph, mechanic: TradeMechanic
    ) -> None:
        """UC-O01 single-tick: swords ↔ coin_pouch; both pending_trade cleared."""
        ctx = MechanicContext(uc_o01_graph, actor="alice", target="bob")
        mechanic.apply(ctx)
        # Items exchanged.
        assert uc_o01_graph.has_edge("bob", "sword")
        assert uc_o01_graph.has_edge("alice", "coin_pouch")
        assert not uc_o01_graph.has_edge("alice", "sword")
        assert not uc_o01_graph.has_edge("bob", "coin_pouch")
        # Pending offers cleared.
        assert uc_o01_graph.query("alice").get("pending_trade") is None
        assert uc_o01_graph.query("bob").get("pending_trade") is None

    def test_asymmetric_intent_refuses(self, mechanic: TradeMechanic) -> None:
        """alice offers sword for shield; bob offers coin for sword. Refuse."""
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            pending_trade={
                "offer_item": "sword",
                "demand_item": "shield",
                "counterparty": "bob",
            },
        )
        kg.add_node(
            "bob",
            node_type="agent",
            pending_trade={
                "offer_item": "coin",
                "demand_item": "sword",
                "counterparty": "alice",
            },
        )
        kg.add_node("sword", node_type="entity")
        kg.add_node("coin", node_type="entity")
        kg.add_edge("alice", "sword", relation="holds")
        kg.add_edge("bob", "coin", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="bob")
        mechanic.apply(ctx)
        # Items unmoved.
        assert kg.has_edge("alice", "sword")
        assert kg.has_edge("bob", "coin")
        assert "asymmetric" in kg.query("alice").get("last_refusal_narrative", "")

    def test_missing_held_item_refuses(self, mechanic: TradeMechanic) -> None:
        """alice offers sword but doesn't actually hold it."""
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            pending_trade={
                "offer_item": "sword",
                "demand_item": "coin",
                "counterparty": "bob",
            },
        )
        kg.add_node(
            "bob",
            node_type="agent",
            pending_trade={
                "offer_item": "coin",
                "demand_item": "sword",
                "counterparty": "alice",
            },
        )
        kg.add_node("sword", node_type="entity")
        kg.add_node("coin", node_type="entity")
        # Note: alice does NOT hold sword.
        kg.add_edge("bob", "coin", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="bob")
        mechanic.apply(ctx)
        assert not kg.has_edge("alice", "coin")
        assert "not held" in kg.query("alice").get("last_refusal_narrative", "")
