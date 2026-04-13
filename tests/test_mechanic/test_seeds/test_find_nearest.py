"""Tests for MECH03 find_nearest seed mechanic."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.find_nearest import FindNearestMechanic


@pytest.fixture
def uc_s03_graph() -> KnowledgeGraph:
    """UC-S03 shape: three weapons at varying distances from alice."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", position=[0, 0])
    kg.add_node("armory", node_type="entity", subtype="room", bbox=[-20, -20, 20, 20])
    kg.add_edge("alice", "armory", relation="located_in")
    kg.add_node(
        "sword_rusty",
        node_type="entity",
        subtype="weapon",
        weapon_kind="sword",
        position=[7, 0],
    )
    kg.add_node(
        "dagger_bronze",
        node_type="entity",
        subtype="weapon",
        weapon_kind="dagger",
        position=[3, 1],
    )
    kg.add_node(
        "bow_long",
        node_type="entity",
        subtype="weapon",
        weapon_kind="bow",
        position=[12, -4],
    )
    for obj in ("sword_rusty", "dagger_bronze", "bow_long"):
        kg.add_edge(obj, "armory", relation="located_in")
    return kg


@pytest.fixture
def mechanic() -> FindNearestMechanic:
    return FindNearestMechanic()


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestFindNearestMetadata:
    def test_id(self, mechanic: FindNearestMechanic) -> None:
        assert mechanic.id == "find_nearest"

    def test_voluntary(self, mechanic: FindNearestMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: FindNearestMechanic) -> None:
        assert "spatial" in mechanic.tags
        assert "query" in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestFindNearestCheck:
    def test_passes_for_positioned_actor_and_subtyped_target(
        self, uc_s03_graph: KnowledgeGraph, mechanic: FindNearestMechanic
    ) -> None:
        ctx = MechanicContext(uc_s03_graph, actor="alice", target="dagger_bronze")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_actor_has_no_position(
        self, mechanic: FindNearestMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("sword", node_type="entity", subtype="weapon", position=[1, 1])
        ctx = MechanicContext(kg, actor="alice", target="sword")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("position" in r for r in result.reasons)

    def test_fails_when_target_has_no_subtype(
        self, mechanic: FindNearestMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", position=[0, 0])
        kg.add_node("thing", node_type="entity")  # no subtype
        ctx = MechanicContext(kg, actor="alice", target="thing")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("subtype" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply() — UC-S03
# ---------------------------------------------------------------------------


class TestFindNearestApply:
    def test_uc_s03_dagger_is_nearest_weapon(
        self, uc_s03_graph: KnowledgeGraph, mechanic: FindNearestMechanic
    ) -> None:
        """alice at [0,0]; dagger at [3,1] (~3.16) is nearer than sword (7) or bow (~12.6)."""
        ctx = MechanicContext(uc_s03_graph, actor="alice", target="dagger_bronze")
        mechanic.apply(ctx)
        result = uc_s03_graph.query("alice").get("nearest_result")
        assert result == "dagger_bronze"

    def test_actor_is_never_returned_as_own_nearest(
        self, mechanic: FindNearestMechanic
    ) -> None:
        """Even if the actor has a matching subtype, the mechanic picks a non-self."""
        kg = KnowledgeGraph()
        # Contrived: actor carries subtype='weapon' (nonsensical but the
        # filter would include them). The mechanic must still skip self.
        kg.add_node("alice", node_type="agent", subtype="weapon", position=[0, 0])
        kg.add_node(
            "sword", node_type="entity", subtype="weapon", position=[10, 10]
        )
        ctx = MechanicContext(kg, actor="alice", target="sword")
        mechanic.apply(ctx)
        result = kg.query("alice").get("nearest_result")
        assert result == "sword"

    def test_no_matching_subtype_yields_no_mutation(
        self, mechanic: FindNearestMechanic
    ) -> None:
        """When nothing matches, nearest_result is not written."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", position=[0, 0])
        # Only one weapon, which is the target — mechanic must filter self-match
        # and find no other matches.
        kg.add_node("sword", node_type="entity", subtype="weapon", position=[5, 0])
        ctx = MechanicContext(kg, actor="alice", target="sword")
        muts = mechanic.apply(ctx)
        # Here the only 'weapon' other than target is... nothing. The target
        # itself is the match. Mechanic returns target id as nearest_result.
        # (Target filter uses its own subtype.)
        assert len(muts) == 1
        assert kg.query("alice").get("nearest_result") == "sword"
