"""Tests for Phase 7 drunk seed mechanic (Plan 07-07, D-01, D-13, D-16, D-18)."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.matchers import VerbMatcher
from token_world.mechanic.seeds.drunk import DrunkMechanic


@pytest.fixture
def mechanic() -> DrunkMechanic:
    return DrunkMechanic()


@pytest.fixture
def drunk_graph() -> KnowledgeGraph:
    """Happy-path graph: alice holds ale with alcohol_content=0.5, sobriety_level=1.0."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", sobriety_level=1.0)
    kg.add_node("tavern", node_type="entity", subtype="room")
    kg.add_node("ale", node_type="entity", subtype="drink", alcohol_content=0.5)
    kg.add_edge("alice", "tavern", relation="located_in")
    kg.add_edge("alice", "ale", relation="holds")
    return kg


# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


class TestDrunkClassAttrs:
    def test_id(self, mechanic: DrunkMechanic) -> None:
        assert mechanic.id == "drunk"

    def test_voluntary(self, mechanic: DrunkMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags_include_social(self, mechanic: DrunkMechanic) -> None:
        assert "social" in mechanic.tags

    def test_tags_include_consciousness(self, mechanic: DrunkMechanic) -> None:
        assert "consciousness" in mechanic.tags

    def test_tags_include_long_running(self, mechanic: DrunkMechanic) -> None:
        assert "long_running" in mechanic.tags


# ---------------------------------------------------------------------------
# watches()
# ---------------------------------------------------------------------------


class TestDrunkWatches:
    def test_watches_returns_verb_matcher_drink(self, mechanic: DrunkMechanic) -> None:
        matchers = mechanic.watches()
        assert len(matchers) == 1
        assert isinstance(matchers[0], VerbMatcher)
        assert matchers[0].verb == "drink"


# ---------------------------------------------------------------------------
# check() — refusal cases
# ---------------------------------------------------------------------------


class TestDrunkCheckRefusals:
    def test_check_refuses_when_no_actor(self, mechanic: DrunkMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("ale", node_type="entity", alcohol_content=0.5)
        ctx = MechanicContext(kg, actor="alice", target="ale")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("actor" in r for r in result.reasons)

    def test_check_refuses_when_no_target(self, mechanic: DrunkMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", sobriety_level=1.0)
        ctx = MechanicContext(kg, actor="alice", target="ale")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("target" in r for r in result.reasons)

    def test_check_refuses_when_actor_does_not_hold_target(self, mechanic: DrunkMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", sobriety_level=1.0)
        kg.add_node("ale", node_type="entity", alcohol_content=0.5)
        # No holds edge
        ctx = MechanicContext(kg, actor="alice", target="ale")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("hold" in r for r in result.reasons)

    def test_check_refuses_when_target_has_no_alcohol_content(
        self, mechanic: DrunkMechanic
    ) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", sobriety_level=1.0)
        kg.add_node("water", node_type="entity", subtype="drink")
        kg.add_edge("alice", "water", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="water")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("alcohol_content" in r for r in result.reasons)

    def test_check_refuses_when_alcohol_content_is_zero(self, mechanic: DrunkMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", sobriety_level=1.0)
        kg.add_node("juice", node_type="entity", alcohol_content=0)
        kg.add_edge("alice", "juice", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="juice")
        result = mechanic.check(ctx)
        assert result.passed is False

    def test_check_refuses_when_alcohol_content_is_negative(self, mechanic: DrunkMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", sobriety_level=1.0)
        kg.add_node("weird_drink", node_type="entity", alcohol_content=-0.1)
        kg.add_edge("alice", "weird_drink", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="weird_drink")
        result = mechanic.check(ctx)
        assert result.passed is False

    def test_check_refuses_when_already_in_lra(self, mechanic: DrunkMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", sobriety_level=0.5)
        kg.set(
            "alice",
            "current_long_action",
            {
                "action_text": "drunk",
                "turns_total": None,
                "turns_elapsed": 2,
                "thresholds": [],
                "payload": {},
            },
        )
        kg.add_node("ale", node_type="entity", alcohol_content=0.5)
        kg.add_edge("alice", "ale", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="ale")
        result = mechanic.check(ctx)
        assert result.passed is False


# ---------------------------------------------------------------------------
# check() — happy path
# ---------------------------------------------------------------------------


class TestDrunkCheckHappyPath:
    def test_check_passes_happy_path(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        assert mechanic.check(ctx).passed is True


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestDrunkApply:
    def test_apply_mutations_order(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        """Mutation order: sobriety_level set, is_drunk=True, remove_node, begin_long_action."""
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        mutations = mechanic.apply(ctx)
        assert len(mutations) == 4
        # Mutation 0: sobriety_level
        assert mutations[0].target == "alice"
        assert mutations[0].property == "sobriety_level"
        # Mutation 1: is_drunk
        assert mutations[1].target == "alice"
        assert mutations[1].property == "is_drunk"
        # Mutation 2: remove ale
        assert mutations[2].target == "ale"
        assert mutations[2].type == "remove_node"
        # Mutation 3: begin_long_action (set current_long_action)
        assert mutations[3].target == "alice"
        assert mutations[3].property == "current_long_action"

    def test_apply_removes_alcohol_target(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        mechanic.apply(ctx)
        assert not drunk_graph.has_node("ale")

    def test_apply_decreases_sobriety_by_alcohol_content(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        """sobriety_level goes from 1.0 to 0.5 (alcohol_content=0.5)."""
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        mechanic.apply(ctx)
        sobriety = drunk_graph.query("alice", "sobriety_level")
        assert abs(sobriety - 0.5) < 1e-9

    def test_apply_sets_is_drunk_true(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        mechanic.apply(ctx)
        assert drunk_graph.query("alice", "is_drunk") is True

    def test_apply_clamps_sobriety_at_zero_minimum(self, mechanic: DrunkMechanic) -> None:
        """Start sobriety=0.3, alcohol_content=0.5 → result should be 0.0."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", sobriety_level=0.3)
        kg.add_node("strongale", node_type="entity", alcohol_content=0.5)
        kg.add_edge("alice", "strongale", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="strongale")
        mechanic.apply(ctx)
        sobriety = kg.query("alice", "sobriety_level")
        assert sobriety == 0.0

    def test_apply_defaults_sobriety_to_1_when_absent(self, mechanic: DrunkMechanic) -> None:
        """Actor without sobriety_level defaults to 1.0 before subtracting alcohol."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")  # no sobriety_level
        kg.add_node("ale", node_type="entity", alcohol_content=0.3)
        kg.add_edge("alice", "ale", relation="holds")
        ctx = MechanicContext(kg, actor="alice", target="ale")
        mechanic.apply(ctx)
        sobriety = kg.query("alice", "sobriety_level")
        assert abs(sobriety - 0.7) < 1e-9

    def test_apply_lra_turns_total_is_none(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        """D-16: indefinite LRA — turns_total must be None specifically."""
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        mechanic.apply(ctx)
        lra = drunk_graph.query("alice", "current_long_action")
        assert lra is not None
        assert lra["turns_total"] is None

    def test_apply_lra_threshold_is_sobriety_gt_0_8(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        """D-18 exact: threshold is sobriety_level > 0.8 (strictly greater)."""
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        mechanic.apply(ctx)
        lra = drunk_graph.query("alice", "current_long_action")
        assert lra is not None
        thresholds = lra["thresholds"]
        assert any(
            t.get("property") == "alice.sobriety_level"
            and t.get("op") == ">"
            and t.get("value") == 0.8
            for t in thresholds
        )

    def test_apply_lra_attention_state_exact_per_d18(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        """D-18 exact: suppress [fine_detail, social_nuance], boost [aggression_level]."""
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        mechanic.apply(ctx)
        lra = drunk_graph.query("alice", "current_long_action")
        attention = lra["payload"]["attention_state"]
        assert attention["suppress"] == ["fine_detail", "social_nuance"]
        assert attention["boost"] == ["aggression_level"]

    def test_apply_lra_action_text_is_drunk(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        mechanic.apply(ctx)
        lra = drunk_graph.query("alice", "current_long_action")
        assert lra["action_text"] == "drunk"

    def test_apply_lra_turns_elapsed_starts_at_zero(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        mechanic.apply(ctx)
        lra = drunk_graph.query("alice", "current_long_action")
        assert lra["turns_elapsed"] == 0

    def test_apply_stores_clear_on_end_in_lra_payload(
        self, drunk_graph: KnowledgeGraph, mechanic: DrunkMechanic
    ) -> None:
        """apply() must include clear_on_end={"is_drunk": False} in the LRA payload (WR-01)."""
        ctx = MechanicContext(drunk_graph, actor="alice", target="ale")
        mechanic.apply(ctx)
        lra = drunk_graph.query("alice", "current_long_action")
        assert "clear_on_end" in lra["payload"]
        assert lra["payload"]["clear_on_end"] == {"is_drunk": False}
