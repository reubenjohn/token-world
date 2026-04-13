"""Tests for MECH05 terrain_move seed mechanic."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.terrain_move import TerrainMoveMechanic


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def swamp_graph() -> KnowledgeGraph:
    """UC-V05 shape: swamp adjacent_to dry_land; swamp has multiplier 2.0."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", move_speed=10, stamina=20, position=[0, 0])
    kg.add_node(
        "swamp",
        node_type="entity",
        subtype="area",
        terrain_type="swamp",
        movement_cost_multiplier=2.0,
    )
    kg.add_node(
        "dry_land",
        node_type="entity",
        subtype="area",
        terrain_type="path",
        movement_cost_multiplier=1.0,
    )
    kg.add_edge("alice", "swamp", relation="located_in")
    kg.add_edge("swamp", "dry_land", relation="adjacent_to")
    kg.add_edge("dry_land", "swamp", relation="adjacent_to")
    return kg


@pytest.fixture
def bridge_graph() -> KnowledgeGraph:
    """UC-S06 shape: alice in room_a; bridge connects to room_b."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", stamina=10)
    kg.add_node("room_a", node_type="entity", subtype="room", terrain_type="floor")
    kg.add_node("room_b", node_type="entity", subtype="room", terrain_type="floor")
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("room_a", "room_b", relation="connects")
    return kg


@pytest.fixture
def mechanic() -> TerrainMoveMechanic:
    return TerrainMoveMechanic()


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestTerrainMoveMetadata:
    def test_id(self, mechanic: TerrainMoveMechanic) -> None:
        assert mechanic.id == "terrain_move"

    def test_voluntary(self, mechanic: TerrainMoveMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: TerrainMoveMechanic) -> None:
        assert "spatial" in mechanic.tags
        assert "terrain" in mechanic.tags


# ---------------------------------------------------------------------------
# terrain_move.check()
# ---------------------------------------------------------------------------


class TestTerrainMoveCheck:
    def test_succeeds_with_multiplier_when_stamina_sufficient(
        self, swamp_graph: KnowledgeGraph, mechanic: TerrainMoveMechanic
    ) -> None:
        ctx = MechanicContext(swamp_graph, actor="alice", target="dry_land")
        result = mechanic.check(ctx)
        assert result.passed is True, f"expected pass, got {result.reasons}"

    def test_fails_when_actor_missing_stamina(
        self, mechanic: TerrainMoveMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")  # no stamina
        kg.add_node(
            "dry_land",
            node_type="entity",
            terrain_type="path",
            movement_cost_multiplier=1.0,
        )
        kg.add_node("here", node_type="entity", terrain_type="floor")
        kg.add_edge("alice", "here", relation="located_in")
        kg.add_edge("here", "dry_land", relation="adjacent_to")
        ctx = MechanicContext(kg, actor="alice", target="dry_land")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("stamina" in r.lower() for r in result.reasons)

    def test_fails_when_target_has_no_terrain(
        self, mechanic: TerrainMoveMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", stamina=10)
        kg.add_node("room_a", node_type="entity")
        kg.add_node("room_b", node_type="entity")  # no terrain_type
        kg.add_edge("alice", "room_a", relation="located_in")
        kg.add_edge("room_a", "room_b", relation="connects")
        ctx = MechanicContext(kg, actor="alice", target="room_b")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("terrain" in r.lower() for r in result.reasons)

    def test_fails_when_stamina_insufficient(
        self, swamp_graph: KnowledgeGraph, mechanic: TerrainMoveMechanic
    ) -> None:
        # Lower alice stamina below swamp's cost.
        swamp_graph.set("alice", "stamina", 1)
        # Base cost of a "swamp" step is the swamp lookup (via source terrain).
        # Make destination expensive too.
        swamp_graph.set("dry_land", "movement_cost_multiplier", 10.0)
        ctx = MechanicContext(swamp_graph, actor="alice", target="dry_land")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("stamina" in r.lower() for r in result.reasons)

    def test_fails_when_terrain_impassable(self, mechanic: TerrainMoveMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", stamina=50)
        kg.add_node("here", node_type="entity", terrain_type="floor")
        kg.add_node("wall", node_type="entity", terrain_type="wall")
        kg.add_edge("alice", "here", relation="located_in")
        kg.add_edge("here", "wall", relation="adjacent_to")
        ctx = MechanicContext(kg, actor="alice", target="wall")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any(
            "impassable" in r.lower() or "wall" in r.lower() for r in result.reasons
        )

    def test_fails_when_no_edge_to_target(self, mechanic: TerrainMoveMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", stamina=10)
        kg.add_node("here", node_type="entity", terrain_type="floor")
        kg.add_node("far", node_type="entity", terrain_type="floor")
        kg.add_edge("alice", "here", relation="located_in")
        # No edge here -> far.
        ctx = MechanicContext(kg, actor="alice", target="far")
        result = mechanic.check(ctx)
        assert result.passed is False


# ---------------------------------------------------------------------------
# terrain_move.apply()
# ---------------------------------------------------------------------------


class TestTerrainMoveApply:
    def test_apply_uc_v05_swamp_to_dry_land(
        self, swamp_graph: KnowledgeGraph, mechanic: TerrainMoveMechanic
    ) -> None:
        """UC-V05: stamina starts at 20, multiplier 2 on source, expects 18."""
        ctx = MechanicContext(swamp_graph, actor="alice", target="dry_land")
        mechanic.apply(ctx)
        assert swamp_graph.query("alice", "stamina") == 18
        assert swamp_graph.has_edge("alice", "dry_land")
        assert not swamp_graph.has_edge("alice", "swamp")

    def test_apply_updates_located_in_edge(
        self, bridge_graph: KnowledgeGraph, mechanic: TerrainMoveMechanic
    ) -> None:
        ctx = MechanicContext(bridge_graph, actor="alice", target="room_b")
        mechanic.apply(ctx)
        assert bridge_graph.has_edge("alice", "room_b")
        edge_data = dict(bridge_graph._graph["alice"]["room_b"])
        assert edge_data.get("relation") == "located_in"
        assert not bridge_graph.has_edge("alice", "room_a")

    def test_apply_sets_location_property(
        self, bridge_graph: KnowledgeGraph, mechanic: TerrainMoveMechanic
    ) -> None:
        ctx = MechanicContext(bridge_graph, actor="alice", target="room_b")
        mechanic.apply(ctx)
        assert bridge_graph.query("alice", "location") == "room_b"
