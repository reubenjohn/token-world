"""Tests for MECH08 give seed mechanic (item + scalar forms)."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.give import GiveMechanic


@pytest.fixture
def mechanic() -> GiveMechanic:
    return GiveMechanic()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestGiveMetadata:
    def test_id(self, mechanic: GiveMechanic) -> None:
        assert mechanic.id == "give"

    def test_voluntary(self, mechanic: GiveMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: GiveMechanic) -> None:
        for tag in ("social", "transfer"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestGiveCheck:
    def test_passes_for_item_form(self, mechanic: GiveMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            pending_give={"item": "sword", "recipient": "bob"},
        )
        kg.add_node("bob", node_type="agent")
        kg.add_node("sword", node_type="entity")
        kg.add_edge("alice", "sword", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        assert mechanic.check(ctx).passed is True

    def test_passes_for_scalar_form(self, mechanic: GiveMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            coin=10,
            pending_give={"property": "coin", "amount": 5, "recipient": "bob"},
        )
        kg.add_node("bob", node_type="agent", coin=0)
        ctx = MechanicContext(kg, actor="alice", target="bob")
        assert mechanic.check(ctx).passed is True

    def test_fails_without_pending_give(self, mechanic: GiveMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("sword", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("pending_give" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply() — item form
# ---------------------------------------------------------------------------


class TestGiveItemForm:
    def test_uc_o03_transfers_held_item(self, mechanic: GiveMechanic) -> None:
        """UC-O03 shape: alice holds sword, gives to bob."""
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            pending_give={"item": "sword", "recipient": "bob"},
        )
        kg.add_node("bob", node_type="agent")
        kg.add_node("sword", node_type="entity", subtype="weapon")
        kg.add_edge("alice", "sword", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="sword")
        mechanic.apply(ctx)
        assert not kg.has_edge("alice", "sword")
        assert kg.has_edge("bob", "sword")
        # pending_give cleared.
        assert kg.query("alice").get("pending_give") is None

    def test_refuses_when_actor_does_not_hold_item(
        self, mechanic: GiveMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            pending_give={"item": "sword", "recipient": "bob"},
        )
        kg.add_node("bob", node_type="agent")
        kg.add_node("sword", node_type="entity")
        # No holds edge.
        ctx = MechanicContext(kg, actor="alice", target="sword")
        mechanic.apply(ctx)
        assert not kg.has_edge("alice", "sword")
        assert not kg.has_edge("bob", "sword")
        assert "not hold" in kg.query("alice").get("last_refusal_narrative", "")


# ---------------------------------------------------------------------------
# apply() — scalar form
# ---------------------------------------------------------------------------


class TestGiveScalarForm:
    def test_uc_r03_gift_currency(self, mechanic: GiveMechanic) -> None:
        """UC-R03: alice has 10 coin, gives bob 5 → alice=5, bob=5."""
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            coin=10,
            pending_give={"property": "coin", "amount": 5, "recipient": "bob"},
        )
        kg.add_node("bob", node_type="agent", coin=0)
        ctx = MechanicContext(kg, actor="alice", target="bob")
        mechanic.apply(ctx)
        assert kg.query("alice").get("coin") == 5
        assert kg.query("bob").get("coin") == 5
        assert kg.query("alice").get("pending_give") is None

    def test_refuses_when_actor_has_insufficient(
        self, mechanic: GiveMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            coin=3,
            pending_give={"property": "coin", "amount": 5, "recipient": "bob"},
        )
        kg.add_node("bob", node_type="agent", coin=0)
        ctx = MechanicContext(kg, actor="alice", target="bob")
        mechanic.apply(ctx)
        # Balances unchanged.
        assert kg.query("alice").get("coin") == 3
        assert kg.query("bob").get("coin") == 0
        assert "insufficient" in kg.query("alice").get("last_refusal_narrative", "")

    def test_preserves_int_ness(self, mechanic: GiveMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            coin=10,
            pending_give={"property": "coin", "amount": 5, "recipient": "bob"},
        )
        kg.add_node("bob", node_type="agent", coin=0)
        ctx = MechanicContext(kg, actor="alice", target="bob")
        mechanic.apply(ctx)
        assert isinstance(kg.query("alice").get("coin"), int)
        assert isinstance(kg.query("bob").get("coin"), int)
