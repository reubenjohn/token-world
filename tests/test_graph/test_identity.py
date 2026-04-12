"""Tests for claim_id identity deconfliction."""

from __future__ import annotations

from token_world.graph.knowledge_graph import KnowledgeGraph


class TestClaimId:
    def test_claim_id_available(self, kg: KnowledgeGraph) -> None:
        """claim_id returns the proposed name when no collision."""
        result = kg.claim_id("wallet")
        assert result == "wallet"

    def test_claim_id_collision(self, kg: KnowledgeGraph) -> None:
        """claim_id returns a suffixed name on collision."""
        kg.add_node("wallet", node_type="entity")
        result = kg.claim_id("wallet")
        assert result != "wallet"
        assert result.startswith("wallet_")

    def test_claim_id_multiple_collisions(self, kg: KnowledgeGraph) -> None:
        """Repeated collisions produce unique IDs."""
        kg.add_node("wallet", node_type="entity")
        id1 = kg.claim_id("wallet")
        # Add the first deconflicted id as a node
        kg.add_node(id1, node_type="entity")
        id2 = kg.claim_id("wallet")
        # All three IDs should be unique
        assert len({id1, id2, "wallet"}) == 3
