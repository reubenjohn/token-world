"""Tests for MECH23 illumination seed mechanic (involuntary).

Per the PLAN's 04-11 environmental cluster:
- ``illumination`` is involuntary; watches PropertyChangeMatcher on ``lit``
  property changes.
- check passes when a target is a light source whose lit property just
  changed and the target is located_in a room that carries an
  ``illumination`` property.
- apply recomputes the containing room's illumination as the sum of
  ``light_radius`` (or ``brightness``) over every located_in-connected
  lit source in that room; mutates ``room.illumination``.
- Reactive-cycle guard: the recompute is idempotent -- repeated apply on
  an already-balanced room is a no-op (zero mutations).
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph, Mutation
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.engine import ChainExecutionEngine
from token_world.mechanic.matchers import PropertyChangeMatcher
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds.illumination import IlluminationMechanic


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mechanic() -> IlluminationMechanic:
    return IlluminationMechanic()


@pytest.fixture
def dark_room_graph() -> KnowledgeGraph:
    """Dark room with an unlit torch."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent")
    kg.add_node("dark_room", node_type="entity", subtype="room", illumination=0)
    kg.add_node(
        "torch",
        node_type="entity",
        subtype="torch",
        lit=False,
        light_radius=5,
    )
    kg.add_edge("torch", "dark_room", relation="located_in")
    kg.add_edge("alice", "dark_room", relation="located_in")
    return kg


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestIlluminationMetadata:
    def test_id(self, mechanic: IlluminationMechanic) -> None:
        assert mechanic.id == "illumination"

    def test_is_involuntary(self, mechanic: IlluminationMechanic) -> None:
        assert mechanic.voluntary is False

    def test_tags_present(self, mechanic: IlluminationMechanic) -> None:
        assert "environmental" in mechanic.tags
        assert "light" in mechanic.tags
        assert "involuntary" in mechanic.tags

    def test_watches_lit_property(self, mechanic: IlluminationMechanic) -> None:
        watchers = mechanic.watches()
        props = {
            m.property_name for m in watchers if isinstance(m, PropertyChangeMatcher)
        }
        assert "lit" in props


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


class TestIlluminationCheck:
    def test_check_passes_lit_torch_in_room(
        self, dark_room_graph: KnowledgeGraph, mechanic: IlluminationMechanic
    ) -> None:
        dark_room_graph.set("torch", "lit", True)
        ctx = MechanicContext(dark_room_graph, actor="torch", target="torch")
        assert mechanic.check(ctx).passed is True

    def test_check_fails_when_target_missing(
        self, mechanic: IlluminationMechanic
    ) -> None:
        kg = KnowledgeGraph()
        ctx = MechanicContext(kg, actor="ghost", target="ghost")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("does not exist" in r for r in result.reasons)

    def test_check_fails_when_target_not_in_room_with_illumination(
        self, mechanic: IlluminationMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("torch", node_type="entity", lit=True, light_radius=5)
        ctx = MechanicContext(kg, actor="torch", target="torch")
        result = mechanic.check(ctx)
        assert result.passed is False


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


class TestIlluminationApply:
    def test_apply_sums_single_lit_source(
        self, dark_room_graph: KnowledgeGraph, mechanic: IlluminationMechanic
    ) -> None:
        dark_room_graph.set("torch", "lit", True)
        ctx = MechanicContext(dark_room_graph, actor="torch", target="torch")
        muts = mechanic.apply(ctx)
        illum = [m for m in muts if m.property == "illumination"]
        assert len(illum) == 1
        assert illum[0].target == "dark_room"
        assert illum[0].new_value == 5

    def test_apply_sums_multiple_lit_sources(
        self, mechanic: IlluminationMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("room", node_type="entity", subtype="room", illumination=0)
        kg.add_node(
            "torch_a", node_type="entity", subtype="torch", lit=True, light_radius=5
        )
        kg.add_node(
            "torch_b", node_type="entity", subtype="torch", lit=True, light_radius=3
        )
        kg.add_node(
            "torch_off", node_type="entity", subtype="torch", lit=False, light_radius=7
        )
        kg.add_edge("torch_a", "room", relation="located_in")
        kg.add_edge("torch_b", "room", relation="located_in")
        kg.add_edge("torch_off", "room", relation="located_in")

        ctx = MechanicContext(kg, actor="torch_a", target="torch_a")
        muts = mechanic.apply(ctx)
        illum = [m for m in muts if m.property == "illumination"]
        assert len(illum) == 1
        # lit sources: torch_a=5 + torch_b=3; unlit torch_off excluded.
        assert illum[0].new_value == 8

    def test_apply_recomputes_to_zero_when_source_extinguished(
        self, mechanic: IlluminationMechanic
    ) -> None:
        """Room that previously had illumination>0 flips back to 0 when
        every occupant is unlit. The idempotent guard only kicks in when
        current equals computed, so a room at illumination=5 with an
        unlit torch must emit a single mutation to 0."""
        kg = KnowledgeGraph()
        kg.add_node("room", node_type="entity", subtype="room", illumination=5)
        kg.add_node(
            "torch", node_type="entity", subtype="torch", lit=False, light_radius=5
        )
        kg.add_edge("torch", "room", relation="located_in")
        ctx = MechanicContext(kg, actor="torch", target="torch")
        muts = mechanic.apply(ctx)
        illum = [m for m in muts if m.property == "illumination"]
        assert len(illum) == 1
        assert illum[0].new_value == 0

    def test_apply_is_idempotent_when_value_unchanged(
        self, mechanic: IlluminationMechanic
    ) -> None:
        """Reactive-cycle guard: if illumination already equals the computed
        total, apply emits zero mutations so the PropertyChangeMatcher does
        not re-trigger illumination indefinitely.
        """
        kg = KnowledgeGraph()
        # Room already has illumination=5 matching the torch's contribution.
        kg.add_node("room", node_type="entity", subtype="room", illumination=5)
        kg.add_node(
            "torch", node_type="entity", subtype="torch", lit=True, light_radius=5
        )
        kg.add_edge("torch", "room", relation="located_in")
        ctx = MechanicContext(kg, actor="torch", target="torch")
        muts = mechanic.apply(ctx)
        assert muts == []


# ---------------------------------------------------------------------------
# Chain execution — UC-V06 end-to-end
# ---------------------------------------------------------------------------


class _LightTorchMechanic(Mechanic):
    """Voluntary helper: sets lit=True on target."""

    id = "light_voluntary"
    description = "Sets lit=True on target (test helper)"
    voluntary = True
    tags: list[str] = []

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["missing"])
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.target, "lit", True)]


class TestIlluminationChain:
    def test_chain_light_torch_propagates_illumination(
        self, dark_room_graph: KnowledgeGraph
    ) -> None:
        """End-to-end: lighting a torch raises room illumination from 0 to 5."""
        engine = ChainExecutionEngine(
            involuntary_mechanics=[IlluminationMechanic()], max_depth=10
        )
        ctx = MechanicContext(dark_room_graph, actor="alice", target="torch")
        trace = engine.execute(_LightTorchMechanic(), ctx)

        assert trace.root.check_result.passed is True
        assert dark_room_graph.query("torch", "lit") is True
        assert dark_room_graph.query("dark_room", "illumination") == 5
