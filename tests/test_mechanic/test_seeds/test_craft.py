"""Tests for MECH14 craft seed mechanic (recipe-driven consumption)."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.craft import CraftMechanic


@pytest.fixture
def mechanic() -> CraftMechanic:
    return CraftMechanic()


@pytest.fixture
def uc_r01_graph() -> KnowledgeGraph:
    """UC-R01 shape: alice at the forge with iron + wood."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", hunger=30, inventory_cap=10)
    kg.add_node(
        "forge",
        node_type="entity",
        subtype="workstation",
        tool_type="forge",
        recipe={
            "inputs": ["iron_ingot", "wood_plank"],
            "output_subtype": "sword",
            "output_name": "sword",
        },
    )
    kg.add_node("smithy", node_type="entity", subtype="room")
    kg.add_node("iron_ingot", node_type="entity", subtype="material", material="iron")
    kg.add_node("wood_plank", node_type="entity", subtype="material", material="wood")
    kg.add_edge("alice", "smithy", relation="located_in")
    kg.add_edge("forge", "smithy", relation="located_in")
    kg.add_edge("alice", "iron_ingot", relation="holds")
    kg.add_edge("alice", "wood_plank", relation="holds")
    return kg


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestCraftMetadata:
    def test_id(self, mechanic: CraftMechanic) -> None:
        assert mechanic.id == "craft"

    def test_voluntary(self, mechanic: CraftMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: CraftMechanic) -> None:
        for tag in ("resource", "crafting"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestCraftCheck:
    def test_passes_for_valid_recipe(
        self, uc_r01_graph: KnowledgeGraph, mechanic: CraftMechanic
    ) -> None:
        ctx = MechanicContext(uc_r01_graph, actor="alice", target="forge")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_target_has_no_recipe(self, mechanic: CraftMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node("rock", node_type="entity")  # no recipe
        ctx = MechanicContext(kg, actor="alice", target="rock")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("recipe" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestCraftApply:
    def test_uc_r01_crafts_sword_from_iron_and_wood(
        self, uc_r01_graph: KnowledgeGraph, mechanic: CraftMechanic
    ) -> None:
        """UC-R01: inputs removed, new sword entity held by alice."""
        ctx = MechanicContext(uc_r01_graph, actor="alice", target="forge")
        mechanic.apply(ctx)
        # Inputs gone.
        assert not uc_r01_graph.has_node("iron_ingot")
        assert not uc_r01_graph.has_node("wood_plank")
        assert not uc_r01_graph.has_edge("alice", "iron_ingot")
        assert not uc_r01_graph.has_edge("alice", "wood_plank")
        # Output: there should be a new sword-subtype entity held by alice.
        held = list(ctx.neighbors("alice", relation="holds"))
        sword_ids = [h for h in held if uc_r01_graph.query(h).get("subtype") == "sword"]
        assert len(sword_ids) == 1
        # inventory_cap preserved on alice.
        assert uc_r01_graph.query("alice").get("inventory_cap") == 10

    def test_claim_id_avoids_collision(self, mechanic: CraftMechanic) -> None:
        """If an existing node already owns the output name, craft claims a suffix."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node(
            "forge",
            node_type="entity",
            recipe={
                "inputs": ["ingot"],
                "output_subtype": "sword",
                "output_name": "sword",
            },
        )
        kg.add_node("ingot", node_type="entity", subtype="material")
        kg.add_edge("alice", "ingot", relation="holds")
        # Pre-existing node claims the id "sword".
        kg.add_node("sword", node_type="entity", subtype="older_sword")
        ctx = MechanicContext(kg, actor="alice", target="forge")
        mechanic.apply(ctx)
        # Old sword untouched; new node has a suffixed id.
        held = list(ctx.neighbors("alice", relation="holds"))
        sword_ids = [h for h in held if kg.query(h).get("subtype") == "sword"]
        assert len(sword_ids) == 1
        assert sword_ids[0] != "sword"  # suffixed
        assert sword_ids[0].startswith("sword_")

    def test_missing_input_refuses(self, mechanic: CraftMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        kg.add_node(
            "forge",
            node_type="entity",
            recipe={"inputs": ["iron_ingot"], "output_subtype": "nail"},
        )
        # alice does not hold iron_ingot.
        kg.add_node("iron_ingot", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="forge")
        mechanic.apply(ctx)
        assert kg.has_node("iron_ingot")  # not consumed
        assert "not held" in kg.query("alice").get("last_refusal_narrative", "")
