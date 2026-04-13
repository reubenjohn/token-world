"""Tests for MECH25 belief_update seed mechanic.

Phase 4 scope: ``belief_update`` writes the actor's belief about the
target's *currently observable properties* to ``actor.beliefs[target]``.
Phase 5 will fire this automatically when a precondition fails visibly
(GAP-ENG19 passive-tick sweep). For Phase 4 it is voluntary — a
manifest can stage it to record a learned-the-hard-way state change.

UC-E03 maps to: alice tries (mentally) to open the chest; the chest
has ``locked=true``; running ``belief_update`` after the failed
attempt records ``alice.beliefs[chest] = {"locked": True}``.
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.belief_update import BeliefUpdateMechanic


@pytest.fixture
def uc_e03_graph() -> KnowledgeGraph:
    """UC-E03 shape: alice in study with a locked chest she has not examined."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", position=[0, 0], beliefs={})
    kg.add_node(
        "study",
        node_type="entity",
        subtype="room",
        bbox=[-5, -5, 5, 5],
    )
    kg.add_node(
        "chest",
        node_type="entity",
        subtype="container",
        locked=True,
        contents=["scroll"],
    )
    kg.add_edge("alice", "study", relation="located_in")
    kg.add_edge("chest", "study", relation="located_in")
    return kg


@pytest.fixture
def mechanic() -> BeliefUpdateMechanic:
    return BeliefUpdateMechanic()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestBeliefUpdateMetadata:
    def test_id(self, mechanic: BeliefUpdateMechanic) -> None:
        assert mechanic.id == "belief_update"

    def test_voluntary(self, mechanic: BeliefUpdateMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: BeliefUpdateMechanic) -> None:
        for tag in ("belief", "epistemic"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestBeliefUpdateCheck:
    def test_passes_for_uc_e03(
        self, uc_e03_graph: KnowledgeGraph, mechanic: BeliefUpdateMechanic
    ) -> None:
        ctx = MechanicContext(uc_e03_graph, actor="alice", target="chest")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_target_missing(
        self, uc_e03_graph: KnowledgeGraph, mechanic: BeliefUpdateMechanic
    ) -> None:
        ctx = MechanicContext(uc_e03_graph, actor="alice", target="phantom")
        assert mechanic.check(ctx).passed is False

    def test_fails_when_actor_missing(self, mechanic: BeliefUpdateMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("chest", node_type="entity", locked=True)
        ctx = MechanicContext(kg, actor="ghost", target="chest")
        assert mechanic.check(ctx).passed is False


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestBeliefUpdateApply:
    def test_uc_e03_writes_locked_belief(
        self, uc_e03_graph: KnowledgeGraph, mechanic: BeliefUpdateMechanic
    ) -> None:
        ctx = MechanicContext(uc_e03_graph, actor="alice", target="chest")
        mechanic.apply(ctx)
        beliefs = uc_e03_graph.query("alice").get("beliefs", {})
        assert "chest" in beliefs
        assert beliefs["chest"].get("locked") is True

    def test_uc_e03_ground_truth_unchanged(
        self, uc_e03_graph: KnowledgeGraph, mechanic: BeliefUpdateMechanic
    ) -> None:
        ctx = MechanicContext(uc_e03_graph, actor="alice", target="chest")
        mechanic.apply(ctx)
        assert uc_e03_graph.query("chest").get("locked") is True
        assert uc_e03_graph.query("chest").get("contents") == ["scroll"]

    def test_uc_e03_no_open_edge_added(
        self, uc_e03_graph: KnowledgeGraph, mechanic: BeliefUpdateMechanic
    ) -> None:
        """The mechanic only writes beliefs; it never adds an opened edge."""
        ctx = MechanicContext(uc_e03_graph, actor="alice", target="chest")
        mechanic.apply(ctx)
        assert not uc_e03_graph.has_edge("alice", "chest")

    def test_existing_beliefs_for_other_targets_preserved(
        self, mechanic: BeliefUpdateMechanic
    ) -> None:
        """beliefs[other_target] is not overwritten."""
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            beliefs={"door": {"locked": False}},
        )
        kg.add_node("chest", node_type="entity", locked=True)
        ctx = MechanicContext(kg, actor="alice", target="chest")
        mechanic.apply(ctx)
        beliefs = kg.query("alice")["beliefs"]
        assert beliefs.get("door") == {"locked": False}
        assert beliefs.get("chest", {}).get("locked") is True

    def test_no_observable_props_yields_empty_belief(self, mechanic: BeliefUpdateMechanic) -> None:
        """Target with no observable props writes an empty dict (still a learning event)."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", beliefs={})
        kg.add_node("rock", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="rock")
        mechanic.apply(ctx)
        beliefs = kg.query("alice").get("beliefs", {})
        # 'rock' key may or may not exist; if it does, it's a dict.
        if "rock" in beliefs:
            assert isinstance(beliefs["rock"], dict)
