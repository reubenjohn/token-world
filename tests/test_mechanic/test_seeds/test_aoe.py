"""Tests for MECH04 aoe seed mechanic."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.aoe import AreaOfEffectMechanic


@pytest.fixture
def uc_s04_graph() -> KnowledgeGraph:
    """UC-S04 shape: fireball at [5,5] radius 3; 3 victims, 2 spared."""
    kg = KnowledgeGraph()
    kg.add_node("mage", node_type="agent", position=[0, 0])
    kg.add_node("field", node_type="entity", subtype="room", bbox=[0, 0, 10, 10])
    kg.add_edge("mage", "field", relation="located_in")
    # Inside radius 3 of [5,5]:
    kg.add_node(
        "barrel_1",
        node_type="entity",
        subtype="barrel",
        position=[5, 5],
        blast_radius=3.0,
        hp=10,
    )
    kg.add_node(
        "barrel_2", node_type="entity", subtype="barrel", position=[6, 7], hp=10
    )
    kg.add_node(
        "goblin_1", node_type="entity", subtype="goblin", position=[4, 4], hp=8
    )
    # Outside radius 3:
    kg.add_node(
        "barrel_3", node_type="entity", subtype="barrel", position=[1, 1], hp=10
    )
    kg.add_node(
        "goblin_2", node_type="entity", subtype="goblin", position=[9, 9], hp=8
    )
    for e in ("barrel_1", "barrel_2", "goblin_1", "barrel_3", "goblin_2"):
        kg.add_edge(e, "field", relation="located_in")
    return kg


@pytest.fixture
def mechanic() -> AreaOfEffectMechanic:
    return AreaOfEffectMechanic()


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestAoeMetadata:
    def test_id(self, mechanic: AreaOfEffectMechanic) -> None:
        assert mechanic.id == "aoe"

    def test_voluntary(self, mechanic: AreaOfEffectMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: AreaOfEffectMechanic) -> None:
        assert "spatial" in mechanic.tags
        assert "aoe" in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestAoeCheck:
    def test_passes_for_positioned_target(
        self, uc_s04_graph: KnowledgeGraph, mechanic: AreaOfEffectMechanic
    ) -> None:
        ctx = MechanicContext(uc_s04_graph, actor="mage", target="barrel_1")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_target_has_no_position(
        self, mechanic: AreaOfEffectMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("mage", node_type="agent")
        kg.add_node("bomb", node_type="entity")  # no position
        ctx = MechanicContext(kg, actor="mage", target="bomb")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("position" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply() — UC-S04 partition
# ---------------------------------------------------------------------------


class TestAoeApply:
    def test_uc_s04_inside_victims_are_damaged(
        self, uc_s04_graph: KnowledgeGraph, mechanic: AreaOfEffectMechanic
    ) -> None:
        """barrel_1, barrel_2, goblin_1 are within radius 3 of [5,5]."""
        ctx = MechanicContext(uc_s04_graph, actor="mage", target="barrel_1")
        mechanic.apply(ctx)
        for victim in ("barrel_1", "barrel_2", "goblin_1"):
            assert uc_s04_graph.query(victim).get("damaged") is True, (
                f"{victim} should be damaged"
            )

    def test_uc_s04_outside_entities_are_spared(
        self, uc_s04_graph: KnowledgeGraph, mechanic: AreaOfEffectMechanic
    ) -> None:
        """barrel_3 and goblin_2 are outside radius 3 — must NOT be damaged."""
        ctx = MechanicContext(uc_s04_graph, actor="mage", target="barrel_1")
        mechanic.apply(ctx)
        for survivor in ("barrel_3", "goblin_2"):
            props = uc_s04_graph.query(survivor)
            assert "damaged" not in props, (
                f"{survivor} should NOT be damaged (outside blast)"
            )

    def test_actor_is_never_damaged_by_own_blast(
        self, uc_s04_graph: KnowledgeGraph, mechanic: AreaOfEffectMechanic
    ) -> None:
        """Move the mage into the blast zone and verify self-damage is suppressed."""
        uc_s04_graph.set("mage", "position", [5, 5])
        ctx = MechanicContext(uc_s04_graph, actor="mage", target="barrel_1")
        mechanic.apply(ctx)
        assert "damaged" not in uc_s04_graph.query("mage")

    def test_room_containers_are_not_damaged(
        self, uc_s04_graph: KnowledgeGraph, mechanic: AreaOfEffectMechanic
    ) -> None:
        """field is subtype=room; even with bbox overlapping the blast, it's skipped."""
        ctx = MechanicContext(uc_s04_graph, actor="mage", target="barrel_1")
        mechanic.apply(ctx)
        assert "damaged" not in uc_s04_graph.query("field")
