"""Tests for the environmental reaction seed mechanic and chain execution."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph, Mutation
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.engine import ChainExecutionEngine
from token_world.mechanic.matchers import PropertyChangeMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds.environmental_reaction import (
    EnvironmentalReactionMechanic,
)


@pytest.fixture
def env_graph() -> KnowledgeGraph:
    """Graph with a campfire, dry leaves (flammable), and wet rock (not flammable)."""
    kg = KnowledgeGraph()
    kg.add_node("campfire", node_type="entity", temperature=200, flammable=False)
    kg.add_node("dry_leaves", node_type="entity", temperature=20, flammable=True)
    kg.add_node("wet_rock", node_type="entity", temperature=20, flammable=False)
    kg.add_edge("campfire", "dry_leaves", relation="adjacent")
    kg.add_edge("campfire", "wet_rock", relation="adjacent")
    return kg


@pytest.fixture
def mechanic() -> EnvironmentalReactionMechanic:
    return EnvironmentalReactionMechanic()


class TestEnvironmentalCheck:
    def test_check_passes_hot_with_flammable_neighbors(
        self, env_graph: KnowledgeGraph, mechanic: EnvironmentalReactionMechanic
    ) -> None:
        ctx = MechanicContext(env_graph, actor="campfire", target="campfire")
        result = mechanic.check(ctx)
        assert result.passed is True

    def test_check_fails_low_temperature(
        self, env_graph: KnowledgeGraph, mechanic: EnvironmentalReactionMechanic
    ) -> None:
        env_graph.set("campfire", "temperature", 50)
        ctx = MechanicContext(env_graph, actor="campfire", target="campfire")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("too low" in r for r in result.reasons)

    def test_check_fails_no_flammable_neighbors(
        self, mechanic: EnvironmentalReactionMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("hot_rock", node_type="entity", temperature=200, flammable=False)
        kg.add_node("cold_rock", node_type="entity", temperature=20, flammable=False)
        kg.add_edge("hot_rock", "cold_rock", relation="adjacent")
        ctx = MechanicContext(kg, actor="hot_rock", target="hot_rock")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("No flammable" in r for r in result.reasons)

    def test_check_fails_target_missing(self, mechanic: EnvironmentalReactionMechanic) -> None:
        kg = KnowledgeGraph()
        ctx = MechanicContext(kg, actor="x", target="nonexistent")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("does not exist" in r for r in result.reasons)

    def test_check_fails_no_temperature(self, mechanic: EnvironmentalReactionMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("thing", node_type="entity")
        ctx = MechanicContext(kg, actor="thing", target="thing")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("No temperature" in r for r in result.reasons)


class TestEnvironmentalApply:
    def test_apply_spreads_fire(
        self, env_graph: KnowledgeGraph, mechanic: EnvironmentalReactionMechanic
    ) -> None:
        ctx = MechanicContext(env_graph, actor="campfire", target="campfire")
        mutations = mechanic.apply(ctx)
        # Should set temperature and on_fire for dry_leaves only
        assert len(mutations) == 2
        temp_mut = [m for m in mutations if m.property == "temperature"]
        fire_mut = [m for m in mutations if m.property == "on_fire"]
        assert len(temp_mut) == 1
        assert temp_mut[0].target == "dry_leaves"
        assert temp_mut[0].new_value == 150
        assert len(fire_mut) == 1
        assert fire_mut[0].target == "dry_leaves"
        assert fire_mut[0].new_value is True
        # wet_rock should be unchanged
        assert env_graph.query("wet_rock", "temperature") == 20

    def test_apply_skips_already_hot(
        self, env_graph: KnowledgeGraph, mechanic: EnvironmentalReactionMechanic
    ) -> None:
        env_graph.set("dry_leaves", "temperature", 150)
        ctx = MechanicContext(env_graph, actor="campfire", target="campfire")
        mutations = mechanic.apply(ctx)
        # dry_leaves already at 150, so no mutations
        assert len(mutations) == 0


class TestEnvironmentalProperties:
    def test_watches_returns_temperature_matcher(
        self, mechanic: EnvironmentalReactionMechanic
    ) -> None:
        watchers = mechanic.watches()
        assert len(watchers) == 1
        assert isinstance(watchers[0], PropertyChangeMatcher)
        assert watchers[0].property_name == "temperature"

    def test_is_involuntary(self, mechanic: EnvironmentalReactionMechanic) -> None:
        assert mechanic.voluntary is False

    def test_id(self, mechanic: EnvironmentalReactionMechanic) -> None:
        assert mechanic.id == "environmental_reaction"


class _SetTemperatureMechanic(Mechanic):
    """Helper voluntary mechanic that sets temperature on target."""

    id = "set_temperature"
    description = "Sets temperature on target node"
    voluntary = True

    def __init__(self, temperature: int = 200) -> None:
        self._temperature = temperature

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["Target missing"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.target, "temperature", self._temperature)]


class TestChainExecution:
    def test_chain_execution_fire_spread(self) -> None:
        """End-to-end D-12 validation: fire spreads recursively through chain engine.

        Setup: A line of flammable entities A--B--C--D, all at temp=20.
        Action: Set A's temperature to 200 via a voluntary mechanic.
        Expected: Fire chains through B, C, D via environmental reaction.
        """
        kg = KnowledgeGraph()
        kg.add_node("node_a", node_type="entity", temperature=20, flammable=True)
        kg.add_node("node_b", node_type="entity", temperature=20, flammable=True)
        kg.add_node("node_c", node_type="entity", temperature=20, flammable=True)
        kg.add_node("node_d", node_type="entity", temperature=20, flammable=True)
        kg.add_node("agent", node_type="agent")
        # Linear chain: A -> B -> C -> D
        kg.add_edge("node_a", "node_b", relation="adjacent")
        kg.add_edge("node_b", "node_c", relation="adjacent")
        kg.add_edge("node_c", "node_d", relation="adjacent")

        env_mechanic = EnvironmentalReactionMechanic()
        engine = ChainExecutionEngine(involuntary_mechanics=[env_mechanic], max_depth=10)

        # Voluntary mechanic sets node_a temperature to 200
        set_temp = _SetTemperatureMechanic(temperature=200)
        ctx = MechanicContext(kg, actor="agent", target="node_a")
        trace = engine.execute(set_temp, ctx)

        # Verify the voluntary mechanic fired
        assert trace.root.check_result.passed is True
        assert trace.root.mechanic_id == "set_temperature"

        # Verify chain depth > 1 (fire actually recursed)
        assert trace.max_depth_reached > 1

        # Verify all nodes caught fire
        assert kg.query("node_a", "temperature") == 200  # set by voluntary mechanic
        assert kg.query("node_b", "temperature") == 150  # chain from A
        assert kg.query("node_b", "on_fire") is True
        assert kg.query("node_c", "temperature") == 150  # chain from B
        assert kg.query("node_c", "on_fire") is True
        assert kg.query("node_d", "temperature") == 150  # chain from C
        assert kg.query("node_d", "on_fire") is True

        # Verify total mechanics: 1 voluntary + 3 involuntary (A->B, B->C, C->D)
        assert trace.total_mechanics_executed >= 4
        assert trace.truncated is False

    def test_chain_stops_at_non_flammable(self) -> None:
        """Chain stops when a node in the path is not flammable."""
        kg = KnowledgeGraph()
        kg.add_node("node_a", node_type="entity", temperature=20, flammable=True)
        kg.add_node("node_b", node_type="entity", temperature=20, flammable=False)
        kg.add_node("node_c", node_type="entity", temperature=20, flammable=True)
        kg.add_node("agent", node_type="agent")
        kg.add_edge("node_a", "node_b", relation="adjacent")
        kg.add_edge("node_b", "node_c", relation="adjacent")

        env_mechanic = EnvironmentalReactionMechanic()
        engine = ChainExecutionEngine(involuntary_mechanics=[env_mechanic])

        set_temp = _SetTemperatureMechanic(temperature=200)
        ctx = MechanicContext(kg, actor="agent", target="node_a")
        engine.execute(set_temp, ctx)

        # node_b is not flammable so it shouldn't catch fire
        assert kg.query("node_b", "temperature") == 20
        # node_c should not be reached since chain stops at node_b
        assert kg.query("node_c", "temperature") == 20
