"""Tests for MECH22 decay_tick seed mechanic (voluntary Phase-4 wrapper).

Per the PLAN's 04-11 environmental cluster:
- ``decay_tick`` is a voluntary wrapper; id="decay_tick", voluntary=True,
  tags=["environmental","decay"].
- check passes when target has ``decay_period`` (int) and ``decay_progress``
  (int, defaulting to 0) and target is not already rotten.
- apply increments decay_progress by 1; if progress >= decay_period, also
  sets ``rotten=True`` and ``freshness="rotten"``.
- Phase-5 GAP-ENG07 will invoke this as a tick-end passive sweep. For
  Phase 4 it's manifest-driven (use-case harness stages the action).
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.decay_tick import DecayTickMechanic

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mechanic() -> DecayTickMechanic:
    return DecayTickMechanic()


@pytest.fixture
def apple_graph() -> KnowledgeGraph:
    """An apple with decay_period=3, decay_progress=0, rotten=False."""
    kg = KnowledgeGraph()
    kg.add_node("engine", node_type="agent")
    kg.add_node(
        "apple",
        node_type="entity",
        subtype="food",
        decay_period=3,
        decay_progress=0,
        rotten=False,
        freshness="fresh",
    )
    return kg


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestDecayTickMetadata:
    def test_id(self, mechanic: DecayTickMechanic) -> None:
        assert mechanic.id == "decay_tick"

    def test_is_voluntary(self, mechanic: DecayTickMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags_present(self, mechanic: DecayTickMechanic) -> None:
        assert "environmental" in mechanic.tags
        assert "decay" in mechanic.tags


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


class TestDecayTickCheck:
    def test_check_passes_fresh_with_period(
        self, apple_graph: KnowledgeGraph, mechanic: DecayTickMechanic
    ) -> None:
        ctx = MechanicContext(apple_graph, actor="engine", target="apple")
        assert mechanic.check(ctx).passed is True

    def test_check_fails_when_target_missing(self, mechanic: DecayTickMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("engine", node_type="agent")
        ctx = MechanicContext(kg, actor="engine", target="ghost")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("does not exist" in r for r in result.reasons)

    def test_check_fails_when_no_decay_period(self, mechanic: DecayTickMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("engine", node_type="agent")
        kg.add_node("rock", node_type="entity")
        ctx = MechanicContext(kg, actor="engine", target="rock")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("decay_period" in r for r in result.reasons)

    def test_check_fails_when_already_rotten(self, mechanic: DecayTickMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("engine", node_type="agent")
        kg.add_node(
            "apple",
            node_type="entity",
            decay_period=3,
            decay_progress=3,
            rotten=True,
        )
        ctx = MechanicContext(kg, actor="engine", target="apple")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("rotten" in r.lower() for r in result.reasons)


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


class TestDecayTickApply:
    def test_apply_increments_decay_progress(
        self, apple_graph: KnowledgeGraph, mechanic: DecayTickMechanic
    ) -> None:
        ctx = MechanicContext(apple_graph, actor="engine", target="apple")
        muts = mechanic.apply(ctx)
        # progress 0 -> 1. No rot flag yet (1 < 3).
        prog_muts = [m for m in muts if m.property == "decay_progress"]
        assert len(prog_muts) == 1
        assert prog_muts[0].new_value == 1
        assert not any(m.property == "rotten" for m in muts)

    def test_apply_sets_rotten_when_progress_reaches_period(
        self, mechanic: DecayTickMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("engine", node_type="agent")
        kg.add_node(
            "apple",
            node_type="entity",
            decay_period=3,
            decay_progress=2,
            rotten=False,
            freshness="fresh",
        )
        ctx = MechanicContext(kg, actor="engine", target="apple")
        muts = mechanic.apply(ctx)
        # progress 2 -> 3; rotten flip fires.
        prog = [m for m in muts if m.property == "decay_progress"]
        rot = [m for m in muts if m.property == "rotten"]
        fresh = [m for m in muts if m.property == "freshness"]
        assert len(prog) == 1 and prog[0].new_value == 3
        assert len(rot) == 1 and rot[0].new_value is True
        assert len(fresh) == 1 and fresh[0].new_value == "rotten"

    def test_apply_three_ticks_chain_to_rotten(
        self, apple_graph: KnowledgeGraph, mechanic: DecayTickMechanic
    ) -> None:
        """End-to-end: run apply 3 times on the apple (UC-V03 intent)."""
        ctx = MechanicContext(apple_graph, actor="engine", target="apple")
        for _ in range(3):
            for m in mechanic.apply(ctx):
                # apply returns mutations already committed (ctx.mutate writes).
                _ = m
        assert apple_graph.query("apple", "decay_progress") == 3
        assert apple_graph.query("apple", "rotten") is True
        assert apple_graph.query("apple", "freshness") == "rotten"

    def test_apply_defaults_decay_progress_to_zero(self, mechanic: DecayTickMechanic) -> None:
        """apple without decay_progress property is treated as progress=0."""
        kg = KnowledgeGraph()
        kg.add_node("engine", node_type="agent")
        kg.add_node(
            "apple",
            node_type="entity",
            decay_period=2,
            rotten=False,
        )
        ctx = MechanicContext(kg, actor="engine", target="apple")
        # Check passes even when decay_progress is absent.
        assert mechanic.check(ctx).passed is True
        muts = mechanic.apply(ctx)
        prog = [m for m in muts if m.property == "decay_progress"]
        assert len(prog) == 1 and prog[0].new_value == 1
