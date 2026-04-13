"""Tests for MECH11 teach seed mechanic.

Phase 4 scope: ``teach`` copies a skill name from ``actor.knows_skill``
to a co-located recipient's ``knows_skill`` list. The DSL has no
indirect_object slot (GAP-ENG02), so the harness routes
``ctx.target`` to the *skill name* (a bare string per UC-O05's
``validator_exception: target_may_not_exist``). The recipient is
discovered via co-location (single co-located agent in scope).

A multi-recipient classroom scenario is out of Phase 4 scope — the
mechanic refuses with a narrative if more than one co-located agent
is eligible.
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.teach import TeachMechanic


@pytest.fixture
def uc_o05_graph() -> KnowledgeGraph:
    """UC-O05 shape: alice teaches lockpicking to bob in the workshop."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", knows_skill=["lockpicking"])
    kg.add_node("bob", node_type="agent", knows_skill=[])
    kg.add_node("workshop", node_type="entity", subtype="room")
    kg.add_node("practice_lock", node_type="entity", subtype="lock")
    kg.add_edge("alice", "workshop", relation="located_in")
    kg.add_edge("bob", "workshop", relation="located_in")
    kg.add_edge("practice_lock", "workshop", relation="located_in")
    return kg


@pytest.fixture
def mechanic() -> TeachMechanic:
    return TeachMechanic()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestTeachMetadata:
    def test_id(self, mechanic: TeachMechanic) -> None:
        assert mechanic.id == "teach"

    def test_voluntary(self, mechanic: TeachMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: TeachMechanic) -> None:
        for tag in ("social", "skill"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestTeachCheck:
    def test_passes_for_uc_o05(
        self, uc_o05_graph: KnowledgeGraph, mechanic: TeachMechanic
    ) -> None:
        ctx = MechanicContext(uc_o05_graph, actor="alice", target="lockpicking")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_actor_does_not_know_skill(
        self, mechanic: TeachMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", knows_skill=[])
        kg.add_node("bob", node_type="agent", knows_skill=[])
        kg.add_node("hall", node_type="entity")
        kg.add_edge("alice", "hall", relation="located_in")
        kg.add_edge("bob", "hall", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="lockpicking")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("knows" in r.lower() or "skill" in r.lower() for r in result.reasons)

    def test_fails_when_no_co_located_agent(self, mechanic: TeachMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", knows_skill=["lockpicking"])
        kg.add_node("workshop", node_type="entity")
        kg.add_edge("alice", "workshop", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="lockpicking")
        assert mechanic.check(ctx).passed is False


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestTeachApply:
    def test_uc_o05_skill_propagates_to_bob(
        self, uc_o05_graph: KnowledgeGraph, mechanic: TeachMechanic
    ) -> None:
        ctx = MechanicContext(uc_o05_graph, actor="alice", target="lockpicking")
        mechanic.apply(ctx)
        assert "lockpicking" in uc_o05_graph.query("bob").get("knows_skill", [])

    def test_uc_o05_actor_still_knows_skill(
        self, uc_o05_graph: KnowledgeGraph, mechanic: TeachMechanic
    ) -> None:
        """Teaching does not erase the teacher's skill."""
        ctx = MechanicContext(uc_o05_graph, actor="alice", target="lockpicking")
        mechanic.apply(ctx)
        assert "lockpicking" in uc_o05_graph.query("alice").get("knows_skill", [])

    def test_recipient_already_knows_skill_is_noop(
        self, mechanic: TeachMechanic
    ) -> None:
        """Re-teaching a known skill leaves bob.knows_skill unchanged."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", knows_skill=["lockpicking"])
        kg.add_node("bob", node_type="agent", knows_skill=["lockpicking"])
        kg.add_node("hall", node_type="entity")
        kg.add_edge("alice", "hall", relation="located_in")
        kg.add_edge("bob", "hall", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="lockpicking")
        mechanic.apply(ctx)
        # Still one entry, not duplicated.
        assert kg.query("bob")["knows_skill"] == ["lockpicking"]
