"""Tests for MECH10 tell seed mechanic.

Phase 4 scope: ``tell`` writes a belief into the recipient's ``beliefs``
dict. It does NOT enforce ground-truth fidelity (that's the partner
GAP-GRAPH04 belief-vs-truth lattice landing in Phase 5). Therefore a
"lie" looks identical to a "truth" at the mechanic level — both
produce the same ``beliefs[about][property] = value`` write.
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.tell import TellMechanic


@pytest.fixture
def uc_o04_graph() -> KnowledgeGraph:
    """UC-O04 shape: alice lies to bob about the chest contents."""
    kg = KnowledgeGraph()
    kg.add_node(
        "alice",
        node_type="agent",
        utterance={"about": "chest", "property": "contents", "value": []},
    )
    kg.add_node("bob", node_type="agent", beliefs={})
    kg.add_node(
        "chest",
        node_type="entity",
        subtype="container",
        contents=["coin:100"],
    )
    kg.add_node("vault", node_type="entity", subtype="room")
    kg.add_edge("alice", "vault", relation="located_in")
    kg.add_edge("bob", "vault", relation="located_in")
    kg.add_edge("chest", "vault", relation="located_in")
    return kg


@pytest.fixture
def mechanic() -> TellMechanic:
    return TellMechanic()


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestTellMetadata:
    def test_id(self, mechanic: TellMechanic) -> None:
        assert mechanic.id == "tell"

    def test_voluntary(self, mechanic: TellMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: TellMechanic) -> None:
        for tag in ("social", "belief"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestTellCheck:
    def test_passes_with_well_shaped_utterance(
        self, uc_o04_graph: KnowledgeGraph, mechanic: TellMechanic
    ) -> None:
        ctx = MechanicContext(uc_o04_graph, actor="alice", target="bob")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_actor_missing(self, mechanic: TellMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("bob", node_type="agent", beliefs={})
        ctx = MechanicContext(kg, actor="ghost", target="bob")
        result = mechanic.check(ctx)
        assert result.passed is False

    def test_fails_when_recipient_missing(
        self, uc_o04_graph: KnowledgeGraph, mechanic: TellMechanic
    ) -> None:
        ctx = MechanicContext(uc_o04_graph, actor="alice", target="ghost")
        result = mechanic.check(ctx)
        assert result.passed is False

    def test_fails_when_utterance_absent(self, mechanic: TellMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("bob", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="bob")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("utterance" in r for r in result.reasons)

    def test_fails_when_utterance_missing_required_keys(self, mechanic: TellMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", utterance={"about": "chest"})
        kg.add_node("bob", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="bob")
        assert mechanic.check(ctx).passed is False


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestTellApply:
    def test_uc_o04_writes_belief_into_recipient(
        self, uc_o04_graph: KnowledgeGraph, mechanic: TellMechanic
    ) -> None:
        """Bob's beliefs[chest][contents] becomes the asserted value
        regardless of ground truth."""
        ctx = MechanicContext(uc_o04_graph, actor="alice", target="bob")
        mechanic.apply(ctx)
        bob_beliefs = uc_o04_graph.query("bob").get("beliefs")
        assert isinstance(bob_beliefs, dict)
        assert bob_beliefs.get("chest") == {"contents": []}

    def test_uc_o04_ground_truth_unchanged(
        self, uc_o04_graph: KnowledgeGraph, mechanic: TellMechanic
    ) -> None:
        """The chest still contains 100 coin — the lie does not mutate reality."""
        ctx = MechanicContext(uc_o04_graph, actor="alice", target="bob")
        mechanic.apply(ctx)
        assert uc_o04_graph.query("chest").get("contents") == ["coin:100"]

    def test_overwrites_existing_belief(self, mechanic: TellMechanic) -> None:
        """A second tell about the same property updates the value."""
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            utterance={"about": "chest", "property": "contents", "value": []},
        )
        kg.add_node(
            "bob",
            node_type="agent",
            beliefs={"chest": {"contents": ["coin:50"]}},
        )
        ctx = MechanicContext(kg, actor="alice", target="bob")
        mechanic.apply(ctx)
        assert kg.query("bob")["beliefs"]["chest"]["contents"] == []

    def test_preserves_unrelated_belief_keys(self, mechanic: TellMechanic) -> None:
        """Existing beliefs about other entities survive."""
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            utterance={"about": "chest", "property": "contents", "value": []},
        )
        kg.add_node(
            "bob",
            node_type="agent",
            beliefs={"door": {"locked": True}},
        )
        ctx = MechanicContext(kg, actor="alice", target="bob")
        mechanic.apply(ctx)
        beliefs = kg.query("bob")["beliefs"]
        assert beliefs.get("door") == {"locked": True}
        assert beliefs.get("chest") == {"contents": []}
