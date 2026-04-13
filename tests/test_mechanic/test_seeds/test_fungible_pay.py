"""Tests for MECH18 fungible_pay seed mechanic + _subset_sum helper.

Subset-sum-driven currency transfer: actor holds N coin entities with
``denomination`` properties; ``actor.pending_payment`` declares a recipient
and an exact target amount; the mechanic finds a held subset whose
denominations sum to the target and transfers those entities (``holds``
edges) to the recipient. Change-making (overpay + emit change-owed) is
``GAP-MECH29``, deferred to Phase 7+; no exact subset means refusal.

UC-R06 routing
--------------
The Phase-3 manifest's classified verb is ``pay``; the harness routes by
``verb`` -> mechanic ``id``, so the manifest's verb is rewritten to
``fungible_pay`` (precedent: 04-09 ``lift -> cooperate``). The
``pending_payment`` dict is pre-staged on alice in the use-case
graph_builder (precedent: 04-08 ``pending_give`` / ``pending_trade`` per the
GAP-ENG02 workaround).
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds._helpers import _subset_sum
from token_world.mechanic.seeds.fungible_pay import FungiblePayMechanic


@pytest.fixture
def mechanic() -> FungiblePayMechanic:
    return FungiblePayMechanic()


@pytest.fixture
def uc_r06_graph() -> KnowledgeGraph:
    """UC-R06 shape: alice holds 5+2+2+1+1=11 coin total; pays shopkeeper 7."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent")
    kg.add_node("shop", node_type="entity", subtype="room")
    kg.add_node("shopkeeper", node_type="agent", coin_received=0)
    kg.add_edge("alice", "shop", relation="located_in")
    kg.add_edge("shopkeeper", "shop", relation="located_in")
    kg.add_node("coin_5", node_type="entity", subtype="coin", denomination=5)
    kg.add_node("coin_2a", node_type="entity", subtype="coin", denomination=2)
    kg.add_node("coin_2b", node_type="entity", subtype="coin", denomination=2)
    kg.add_node("coin_1a", node_type="entity", subtype="coin", denomination=1)
    kg.add_node("coin_1b", node_type="entity", subtype="coin", denomination=1)
    for c in ("coin_5", "coin_2a", "coin_2b", "coin_1a", "coin_1b"):
        kg.add_edge("alice", c, relation="holds")
    # Stage the GAP-ENG02 workaround: who, how much, what kind.
    kg.set("alice", "pending_payment", {"recipient": "shopkeeper", "amount": 7, "kind": "coin"})
    return kg


# ---------------------------------------------------------------------------
# Helper: _subset_sum
# ---------------------------------------------------------------------------


class TestSubsetSum:
    """Backtracking subset-sum that returns a list of indices into *values*.

    The implementation is exponential in the number of held coins; Phase-4
    use cases stay well below the practical wall (~20 coins). The helper
    returns ``None`` when no exact subset exists.
    """

    def test_finds_exact_single_value(self) -> None:
        idxs = _subset_sum([7], 7)
        assert idxs == [0]

    def test_finds_exact_pair(self) -> None:
        idxs = _subset_sum([5, 2], 7)
        assert idxs is not None
        assert sorted(idxs) == [0, 1]

    def test_finds_uc_r06_subset(self) -> None:
        """5+2 OR 5+1+1 OR 2+2+2+1 all sum to 7; any one is acceptable."""
        idxs = _subset_sum([5, 2, 2, 1, 1], 7)
        assert idxs is not None
        chosen = sorted(5 if i == 0 else (2 if i in (1, 2) else 1) for i in idxs)
        assert sum(chosen) == 7

    def test_returns_none_when_no_subset(self) -> None:
        # 5 + 5 + 5 = 15; cannot make 4.
        assert _subset_sum([5, 5, 5], 4) is None

    def test_handles_empty_list(self) -> None:
        assert _subset_sum([], 7) is None
        # The trivial empty-sum case: target 0 with empty list is not a
        # legal payment (no entities to transfer); the helper returns
        # None for it so the caller doesn't transfer nothing.
        assert _subset_sum([], 0) is None

    def test_returns_none_for_zero_target_with_values(self) -> None:
        """Paying 0 is not a meaningful transfer; helper returns None."""
        assert _subset_sum([1, 2, 3], 0) is None

    def test_returns_none_for_negative_target(self) -> None:
        assert _subset_sum([1, 2, 3], -5) is None


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestFungiblePayMetadata:
    def test_id(self, mechanic: FungiblePayMechanic) -> None:
        assert mechanic.id == "fungible_pay"

    def test_voluntary(self, mechanic: FungiblePayMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: FungiblePayMechanic) -> None:
        for tag in ("resource", "currency"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestFungiblePayCheck:
    def test_passes_for_uc_r06_shape(
        self, uc_r06_graph: KnowledgeGraph, mechanic: FungiblePayMechanic
    ) -> None:
        ctx = MechanicContext(uc_r06_graph, actor="alice", target="shopkeeper")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_actor_missing(self, mechanic: FungiblePayMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("shopkeeper", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="shopkeeper")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("actor" in r for r in result.reasons)

    def test_fails_when_pending_payment_missing(
        self, mechanic: FungiblePayMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("shopkeeper", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="shopkeeper")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("pending_payment" in r for r in result.reasons)

    def test_fails_when_pending_payment_missing_recipient(
        self, mechanic: FungiblePayMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("shopkeeper", node_type="agent")
        kg.set("alice", "pending_payment", {"amount": 5, "kind": "coin"})
        ctx = MechanicContext(kg, actor="alice", target="shopkeeper")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("recipient" in r for r in result.reasons)

    def test_fails_when_pending_payment_missing_amount(
        self, mechanic: FungiblePayMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("shopkeeper", node_type="agent")
        kg.set("alice", "pending_payment", {"recipient": "shopkeeper", "kind": "coin"})
        ctx = MechanicContext(kg, actor="alice", target="shopkeeper")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("amount" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestFungiblePayApply:
    def test_uc_r06_happy_path_transfers_exact_subset(
        self, uc_r06_graph: KnowledgeGraph, mechanic: FungiblePayMechanic
    ) -> None:
        """Target 7 from {5, 2, 2, 1, 1}: a subset summing to 7 transfers."""
        ctx = MechanicContext(uc_r06_graph, actor="alice", target="shopkeeper")
        mechanic.apply(ctx)

        # Sum of denominations now held by shopkeeper must equal 7.
        moved_total = 0
        for c in ("coin_5", "coin_2a", "coin_2b", "coin_1a", "coin_1b"):
            if uc_r06_graph.has_edge("shopkeeper", c):
                moved_total += uc_r06_graph.query(c).get("denomination") or 0
        assert moved_total == 7

        # Conservation: every coin still held by exactly one party.
        for c in ("coin_5", "coin_2a", "coin_2b", "coin_1a", "coin_1b"):
            held_by_alice = uc_r06_graph.has_edge("alice", c)
            held_by_shop = uc_r06_graph.has_edge("shopkeeper", c)
            assert held_by_alice ^ held_by_shop, (
                f"{c}: must be held by exactly one party "
                f"(alice={held_by_alice}, shop={held_by_shop})"
            )

        # pending_payment cleared.
        assert uc_r06_graph.query("alice").get("pending_payment") is None

    def test_single_coin_exact_match(self, mechanic: FungiblePayMechanic) -> None:
        """Holding one 7-coin; pay 7 transfers just that coin."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("bob", node_type="agent")
        kg.add_node("coin_7", node_type="entity", subtype="coin", denomination=7)
        kg.add_edge("alice", "coin_7", relation="holds")
        kg.set("alice", "pending_payment", {"recipient": "bob", "amount": 7, "kind": "coin"})
        ctx = MechanicContext(kg, actor="alice", target="bob")
        mechanic.apply(ctx)

        assert kg.has_edge("bob", "coin_7")
        assert not kg.has_edge("alice", "coin_7")
        assert kg.query("alice").get("pending_payment") is None

    def test_no_subset_refuses_with_change_narrative(
        self, mechanic: FungiblePayMechanic
    ) -> None:
        """Holding only 5s and 2s: cannot make exactly 4 -> refuse w/ GAP-MECH29."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("bob", node_type="agent")
        kg.add_node("coin_5", node_type="entity", subtype="coin", denomination=5)
        kg.add_node("coin_2", node_type="entity", subtype="coin", denomination=2)
        kg.add_edge("alice", "coin_5", relation="holds")
        kg.add_edge("alice", "coin_2", relation="holds")
        kg.set("alice", "pending_payment", {"recipient": "bob", "amount": 4, "kind": "coin"})
        ctx = MechanicContext(kg, actor="alice", target="bob")
        mechanic.apply(ctx)

        # No transfer happened; both coins still held by alice.
        assert kg.has_edge("alice", "coin_5")
        assert kg.has_edge("alice", "coin_2")
        assert not kg.has_edge("bob", "coin_5")
        assert not kg.has_edge("bob", "coin_2")
        # Refusal narrative emitted with the deferred-gap reason.
        narrative = kg.query("alice").get("last_refusal_narrative") or ""
        assert "exact" in narrative or "change" in narrative
        # pending_payment is NOT cleared on refusal -- the agent may try
        # again with a different payment shape.
        assert kg.query("alice").get("pending_payment") is not None

    def test_recipient_missing_refuses(self, mechanic: FungiblePayMechanic) -> None:
        """Recipient node absent -> refuse, no graph mutations beyond narrative."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("coin_5", node_type="entity", subtype="coin", denomination=5)
        kg.add_edge("alice", "coin_5", relation="holds")
        kg.set("alice", "pending_payment", {"recipient": "ghost", "amount": 5, "kind": "coin"})
        ctx = MechanicContext(kg, actor="alice", target="ghost")
        # check() should refuse on the missing recipient (which is also the
        # ctx.target here) -- this matches the consume/give refusal idiom.
        result = mechanic.check(ctx)
        assert result.passed is False

    def test_only_matching_kind_coins_are_eligible(
        self, mechanic: FungiblePayMechanic
    ) -> None:
        """Held entities of a different fungible_kind / wrong subtype are skipped."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("bob", node_type="agent")
        # A coin and a non-coin held entity with the same numeric prop.
        kg.add_node("coin_5", node_type="entity", subtype="coin", denomination=5)
        kg.add_node("rock", node_type="entity", subtype="rock", denomination=5)
        kg.add_edge("alice", "coin_5", relation="holds")
        kg.add_edge("alice", "rock", relation="holds")
        kg.set("alice", "pending_payment", {"recipient": "bob", "amount": 5, "kind": "coin"})
        ctx = MechanicContext(kg, actor="alice", target="bob")
        mechanic.apply(ctx)

        # Only the coin moved; the rock stays with alice.
        assert kg.has_edge("bob", "coin_5")
        assert not kg.has_edge("alice", "coin_5")
        assert kg.has_edge("alice", "rock")
        assert not kg.has_edge("bob", "rock")
