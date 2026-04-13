"""Tests for Phase 7 sober_up passive seed mechanic (Plan 07-07, D-01, D-18)."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.matchers import TickMatcher
from token_world.mechanic.seeds.sober_up import RECOVERY_RATE, SoberUpMechanic


@pytest.fixture
def mechanic() -> SoberUpMechanic:
    return SoberUpMechanic()


def _make_drunk_ctx(sobriety: float = 0.5) -> tuple[KnowledgeGraph, MechanicContext]:
    """Helper: one drunk agent with given sobriety, sentinel target."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", is_drunk=True, sobriety_level=sobriety)
    kg.add_node("sentinel", node_type="entity")
    ctx = MechanicContext(kg, actor="sentinel", target="sentinel")
    return kg, ctx


# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


class TestSoberUpClassAttrs:
    def test_id(self, mechanic: SoberUpMechanic) -> None:
        assert mechanic.id == "sober_up"

    def test_voluntary_is_false(self, mechanic: SoberUpMechanic) -> None:
        assert mechanic.voluntary is False

    def test_tags_include_social(self, mechanic: SoberUpMechanic) -> None:
        assert "social" in mechanic.tags

    def test_tags_include_consciousness(self, mechanic: SoberUpMechanic) -> None:
        assert "consciousness" in mechanic.tags

    def test_tags_include_passive(self, mechanic: SoberUpMechanic) -> None:
        assert "passive" in mechanic.tags

    def test_recovery_rate_constant(self) -> None:
        assert RECOVERY_RATE == 0.1


# ---------------------------------------------------------------------------
# watches()
# ---------------------------------------------------------------------------


class TestSoberUpWatches:
    def test_watches_returns_tick_matcher(self, mechanic: SoberUpMechanic) -> None:
        matchers = mechanic.watches()
        assert len(matchers) == 1
        assert isinstance(matchers[0], TickMatcher)


# ---------------------------------------------------------------------------
# check() — refusal cases
# ---------------------------------------------------------------------------


class TestSoberUpCheckRefusals:
    def test_check_refuses_when_no_drunk_actors(self, mechanic: SoberUpMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", sobriety_level=1.0)  # not drunk
        kg.add_node("sentinel", node_type="entity")
        ctx = MechanicContext(kg, actor="sentinel", target="sentinel")
        result = mechanic.check(ctx)
        assert result.passed is False

    def test_check_refuses_when_drunk_actor_already_at_max_sobriety(
        self, mechanic: SoberUpMechanic
    ) -> None:
        """is_drunk=True but sobriety=1.0 — nothing to recover."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", is_drunk=True, sobriety_level=1.0)
        kg.add_node("sentinel", node_type="entity")
        ctx = MechanicContext(kg, actor="sentinel", target="sentinel")
        result = mechanic.check(ctx)
        assert result.passed is False

    def test_check_refuses_when_empty_graph(self, mechanic: SoberUpMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("sentinel", node_type="entity")
        ctx = MechanicContext(kg, actor="sentinel", target="sentinel")
        result = mechanic.check(ctx)
        assert result.passed is False


# ---------------------------------------------------------------------------
# check() — happy path
# ---------------------------------------------------------------------------


class TestSoberUpCheckHappyPath:
    def test_check_passes_when_at_least_one_drunk_actor_below_max(
        self, mechanic: SoberUpMechanic
    ) -> None:
        _, ctx = _make_drunk_ctx(sobriety=0.5)
        assert mechanic.check(ctx).passed is True

    def test_check_passes_with_sobriety_just_below_max(self, mechanic: SoberUpMechanic) -> None:
        _, ctx = _make_drunk_ctx(sobriety=0.99)
        assert mechanic.check(ctx).passed is True


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestSoberUpApply:
    def test_apply_increments_sobriety_by_recovery_rate(self, mechanic: SoberUpMechanic) -> None:
        """0.5 → 0.6 (RECOVERY_RATE=0.1)."""
        kg, ctx = _make_drunk_ctx(sobriety=0.5)
        mechanic.apply(ctx)
        new_sobriety = kg.query("alice", "sobriety_level")
        assert abs(new_sobriety - 0.6) < 1e-9

    def test_apply_clamps_at_1_0_maximum(self, mechanic: SoberUpMechanic) -> None:
        """0.95 + 0.1 = 1.05 → clamped to 1.0."""
        kg, ctx = _make_drunk_ctx(sobriety=0.95)
        mechanic.apply(ctx)
        new_sobriety = kg.query("alice", "sobriety_level")
        assert new_sobriety == 1.0

    def test_apply_handles_missing_sobriety_level_as_zero(self, mechanic: SoberUpMechanic) -> None:
        """Actor is_drunk=True with no sobriety_level prop → defaults to 0.0, becomes 0.1."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", is_drunk=True)  # no sobriety_level
        kg.add_node("sentinel", node_type="entity")
        ctx = MechanicContext(kg, actor="sentinel", target="sentinel")
        mechanic.apply(ctx)
        new_sobriety = kg.query("alice", "sobriety_level")
        assert abs(new_sobriety - 0.1) < 1e-9

    def test_apply_does_not_clear_lra(self, mechanic: SoberUpMechanic) -> None:
        """LRA must still be present after sober_up fires — hook owns LRA lifecycle."""
        kg = KnowledgeGraph()
        lra = {
            "action_text": "drunk",
            "turns_total": None,
            "turns_elapsed": 3,
            "thresholds": [{"property": "alice.sobriety_level", "op": ">", "value": 0.8}],
            "payload": {},
        }
        kg.add_node("alice", node_type="agent", is_drunk=True, sobriety_level=0.5)
        kg.set("alice", "current_long_action", lra)
        kg.add_node("sentinel", node_type="entity")
        ctx = MechanicContext(kg, actor="sentinel", target="sentinel")
        mechanic.apply(ctx)
        remaining_lra = kg.query("alice", "current_long_action")
        assert remaining_lra is not None
        assert remaining_lra["action_text"] == "drunk"

    def test_apply_does_not_set_is_drunk_false(self, mechanic: SoberUpMechanic) -> None:
        """After sober_up, is_drunk must still be True — hook clears it on threshold fire."""
        kg, ctx = _make_drunk_ctx(sobriety=0.5)
        mechanic.apply(ctx)
        assert kg.query("alice", "is_drunk") is True

    def test_apply_does_not_advance_non_drunk_actors(self, mechanic: SoberUpMechanic) -> None:
        """Non-drunk actors must not have their sobriety_level touched."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", is_drunk=True, sobriety_level=0.5)
        kg.add_node("bob", node_type="agent", sobriety_level=0.8)  # is_drunk not set
        kg.add_node("sentinel", node_type="entity")
        ctx = MechanicContext(kg, actor="sentinel", target="sentinel")
        mechanic.apply(ctx)
        # bob's sobriety should be unchanged
        assert kg.query("bob", "sobriety_level") == 0.8
        # alice's sobriety should have advanced
        assert abs(kg.query("alice", "sobriety_level") - 0.6) < 1e-9

    def test_apply_advances_all_drunk_actors(self, mechanic: SoberUpMechanic) -> None:
        """Multiple drunk actors all get sobriety incremented."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", is_drunk=True, sobriety_level=0.3)
        kg.add_node("bob", node_type="agent", is_drunk=True, sobriety_level=0.6)
        kg.add_node("sentinel", node_type="entity")
        ctx = MechanicContext(kg, actor="sentinel", target="sentinel")
        mechanic.apply(ctx)
        assert abs(kg.query("alice", "sobriety_level") - 0.4) < 1e-9
        assert abs(kg.query("bob", "sobriety_level") - 0.7) < 1e-9

    def test_apply_returns_one_mutation_per_drunk_actor(self, mechanic: SoberUpMechanic) -> None:
        """apply() returns exactly one mutation per recovering drunk actor."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", is_drunk=True, sobriety_level=0.5)
        kg.add_node("bob", node_type="agent", is_drunk=True, sobriety_level=0.6)
        kg.add_node("sentinel", node_type="entity")
        ctx = MechanicContext(kg, actor="sentinel", target="sentinel")
        mutations = mechanic.apply(ctx)
        assert len(mutations) == 2
