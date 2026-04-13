"""Tests for MECH20 fire_spread seed mechanic (involuntary).

Per the PLAN's 04-11 environmental cluster:
- ``fire_spread`` is involuntary; watches ``PropertyChangeMatcher`` on
  ``temperature`` and ``on_fire`` property changes.
- check passes when the target has ``on_fire=True`` and at least one
  flammable neighbour is not already on fire (reactive-cycle guard per
  GAP-MECH26).
- apply sets ``on_fire=True`` and ``temperature=150`` on each flammable
  neighbour that is not already on fire -- single-hop spread per tick,
  cascades via the chain engine.
- Reactive-cycle guard test: does NOT re-ignite already-burning nodes.
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph, Mutation
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.engine import ChainExecutionEngine
from token_world.mechanic.matchers import PropertyChangeMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds.fire_spread import FireSpreadMechanic

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mechanic() -> FireSpreadMechanic:
    return FireSpreadMechanic()


@pytest.fixture
def fire_graph() -> KnowledgeGraph:
    """Burning torch adjacent to a flammable table and a stone wall.

    - torch: on_fire=True, temperature=150, flammable=True
    - wooden_table: flammable=True, temperature=20, on_fire=False
    - stone_wall: flammable=False
    """
    kg = KnowledgeGraph()
    kg.add_node("torch", node_type="entity", on_fire=True, temperature=150, flammable=True)
    kg.add_node(
        "wooden_table",
        node_type="entity",
        on_fire=False,
        temperature=20,
        flammable=True,
    )
    kg.add_node("stone_wall", node_type="entity", flammable=False, temperature=20)
    kg.add_edge("torch", "wooden_table", relation="adjacent")
    kg.add_edge("torch", "stone_wall", relation="adjacent")
    return kg


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestFireSpreadMetadata:
    def test_id(self, mechanic: FireSpreadMechanic) -> None:
        assert mechanic.id == "fire_spread"

    def test_is_voluntary_for_routing(self, mechanic: FireSpreadMechanic) -> None:
        """Phase-4 routing: voluntary=True so UC-V01's verb can match.

        Semantic intent is reactive / involuntary (recorded by the
        ``involuntary_intent`` tag and retained ``watches()``); the
        flag is True only so ``match_mechanic_for_verb`` can route
        UC-V01 to the mechanic under the Phase-4 harness. Phase 5
        flips back to False when a proper classifier + involuntary-
        registration wiring lands.
        """
        assert mechanic.voluntary is True
        # Reactive matchers still declared for future Phase-5 wiring.
        assert mechanic.watches() != []

    def test_tags_present(self, mechanic: FireSpreadMechanic) -> None:
        assert "environmental" in mechanic.tags
        assert "fire" in mechanic.tags
        assert "involuntary_intent" in mechanic.tags

    def test_watches_temperature_and_on_fire(self, mechanic: FireSpreadMechanic) -> None:
        watchers = mechanic.watches()
        # At least one PropertyChangeMatcher for temperature and one for on_fire.
        props = {m.property_name for m in watchers if isinstance(m, PropertyChangeMatcher)}
        assert "temperature" in props
        assert "on_fire" in props


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


class TestFireSpreadCheck:
    def test_check_passes_on_fire_with_flammable_neighbor(
        self, fire_graph: KnowledgeGraph, mechanic: FireSpreadMechanic
    ) -> None:
        ctx = MechanicContext(fire_graph, actor="torch", target="torch")
        result = mechanic.check(ctx)
        assert result.passed is True

    def test_check_fails_when_target_missing(self, mechanic: FireSpreadMechanic) -> None:
        kg = KnowledgeGraph()
        ctx = MechanicContext(kg, actor="x", target="ghost")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("does not exist" in r for r in result.reasons)

    def test_check_fails_when_target_not_on_fire(self, mechanic: FireSpreadMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node(
            "torch",
            node_type="entity",
            on_fire=False,
            temperature=20,
            flammable=True,
        )
        kg.add_node("wooden_table", node_type="entity", flammable=True, on_fire=False)
        kg.add_edge("torch", "wooden_table", relation="adjacent")
        ctx = MechanicContext(kg, actor="torch", target="torch")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("not on fire" in r.lower() for r in result.reasons)

    def test_check_fails_when_no_flammable_neighbors(self, mechanic: FireSpreadMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("torch", node_type="entity", on_fire=True, flammable=True)
        kg.add_node("stone_wall", node_type="entity", flammable=False)
        kg.add_edge("torch", "stone_wall", relation="adjacent")
        ctx = MechanicContext(kg, actor="torch", target="torch")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any(
            "no flammable" in r.lower() or "not flammable" in r.lower() for r in result.reasons
        )

    def test_check_fails_when_all_flammable_neighbors_already_on_fire(
        self, mechanic: FireSpreadMechanic
    ) -> None:
        """Reactive-cycle guard: do not re-fire nodes already on fire.

        Per PLAN threat_model T-04-CYCLE: the mechanic's check() refuses
        when every flammable neighbour is already on_fire=True, so the
        chain engine's reactive loop cannot reprocess them.
        """
        kg = KnowledgeGraph()
        kg.add_node("a", node_type="entity", on_fire=True, flammable=True)
        kg.add_node("b", node_type="entity", on_fire=True, flammable=True)
        kg.add_edge("a", "b", relation="adjacent")
        ctx = MechanicContext(kg, actor="a", target="a")
        result = mechanic.check(ctx)
        assert result.passed is False


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


class TestFireSpreadApply:
    def test_apply_ignites_flammable_neighbor(
        self, fire_graph: KnowledgeGraph, mechanic: FireSpreadMechanic
    ) -> None:
        ctx = MechanicContext(fire_graph, actor="torch", target="torch")
        muts = mechanic.apply(ctx)
        # Two mutations per ignited neighbour: on_fire + temperature.
        targets = {m.target for m in muts}
        assert "wooden_table" in targets
        assert "stone_wall" not in targets  # not flammable
        props = {m.property for m in muts}
        assert "on_fire" in props
        assert "temperature" in props

    def test_apply_does_not_reignite_already_burning(self, mechanic: FireSpreadMechanic) -> None:
        """Reactive-cycle guard: already-on-fire neighbors receive no mutation.

        Critical for T-04-CYCLE mitigation: when a chain execution
        fires fire_spread on a target whose neighbour is already
        burning, the helper must emit zero mutations for that
        neighbour (otherwise the engine's matcher would re-trigger
        fire_spread on the 'changed' on_fire property and loop).
        """
        kg = KnowledgeGraph()
        kg.add_node("torch", node_type="entity", on_fire=True, flammable=True, temperature=150)
        kg.add_node(
            "already_burning",
            node_type="entity",
            on_fire=True,
            flammable=True,
            temperature=150,
        )
        kg.add_node("fresh_wood", node_type="entity", on_fire=False, flammable=True, temperature=20)
        kg.add_edge("torch", "already_burning", relation="adjacent")
        kg.add_edge("torch", "fresh_wood", relation="adjacent")
        ctx = MechanicContext(kg, actor="torch", target="torch")
        muts = mechanic.apply(ctx)
        # Only fresh_wood should see mutations; already_burning must not.
        targets = {m.target for m in muts}
        assert "fresh_wood" in targets
        assert "already_burning" not in targets


# ---------------------------------------------------------------------------
# Chain execution (single-hop + cascade) via engine
# ---------------------------------------------------------------------------


class _IgniteMechanic(Mechanic):
    """Voluntary helper that sets on_fire=True + temperature=150 on target."""

    id = "ignite_voluntary"
    description = "Sets on_fire=True on target (test helper)"
    voluntary = True
    tags: list[str] = []

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["missing"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [
            ctx.mutate(ctx.target, "on_fire", True),
            ctx.mutate(ctx.target, "temperature", 150),
        ]


class TestFireSpreadChain:
    def test_chain_spreads_to_single_flammable_neighbor(self) -> None:
        """End-to-end: voluntary ignite triggers fire_spread on the neighbour."""
        kg = KnowledgeGraph()
        kg.add_node("agent", node_type="agent")
        kg.add_node(
            "torch",
            node_type="entity",
            on_fire=False,
            temperature=20,
            flammable=True,
        )
        kg.add_node(
            "wooden_table",
            node_type="entity",
            on_fire=False,
            temperature=20,
            flammable=True,
        )
        kg.add_edge("torch", "wooden_table", relation="adjacent")

        engine = ChainExecutionEngine(involuntary_mechanics=[FireSpreadMechanic()], max_depth=10)
        ctx = MechanicContext(kg, actor="agent", target="torch")
        trace = engine.execute(_IgniteMechanic(), ctx)

        assert trace.root.check_result.passed is True
        assert kg.query("torch", "on_fire") is True
        assert kg.query("wooden_table", "on_fire") is True
        assert kg.query("wooden_table", "temperature") == 150
