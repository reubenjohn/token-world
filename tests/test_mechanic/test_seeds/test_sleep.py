"""Unit tests for the sleep seed mechanic (Plan 07-05, D-18).

Coverage:
- Class attributes: id, description, voluntary, tags
- watches() returns VerbMatcher(verb='sleep')
- check() passes/refuses for: missing actor, active LRA, no LRA, None LRA
- apply() mutations order and shape
- apply() thresholds: with location (noise + health), without location (health only),
  location referencing missing node (health only)
- apply() attention_state structure
- turns_total == 8 exact
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.matchers import VerbMatcher
from token_world.mechanic.seeds.sleep import SleepMechanic

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mech() -> SleepMechanic:
    return SleepMechanic()


@pytest.fixture
def kg_with_bedroom() -> KnowledgeGraph:
    """Graph with alice in a bedroom."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", location="bedroom", health=0.8)
    kg.add_node("bedroom", node_type="entity", noise_level=0.3)
    return kg


@pytest.fixture
def kg_no_location() -> KnowledgeGraph:
    """Graph with alice but no location property."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", health=0.8)
    return kg


@pytest.fixture
def kg_ghost_room() -> KnowledgeGraph:
    """Graph with alice whose location references a node that doesn't exist."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", location="ghost_room", health=0.8)
    return kg


def _ctx(kg: KnowledgeGraph, actor: str = "alice") -> MechanicContext:
    return MechanicContext(kg, actor=actor, target=actor, tick_id="tick_1", universe_seed=42)


# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


class TestSleepClassAttrs:
    def test_id(self, mech: SleepMechanic) -> None:
        assert mech.id == "sleep"

    def test_description_is_non_empty(self, mech: SleepMechanic) -> None:
        assert isinstance(mech.description, str)
        assert len(mech.description) > 0

    def test_voluntary_is_true(self, mech: SleepMechanic) -> None:
        assert mech.voluntary is True

    def test_tags_contains_rest(self, mech: SleepMechanic) -> None:
        assert "rest" in mech.tags

    def test_tags_contains_long_running(self, mech: SleepMechanic) -> None:
        assert "long_running" in mech.tags


# ---------------------------------------------------------------------------
# watches()
# ---------------------------------------------------------------------------


class TestSleepWatches:
    def test_watches_returns_verb_matcher_sleep(self, mech: SleepMechanic) -> None:
        matchers = mech.watches()
        assert len(matchers) == 1
        assert isinstance(matchers[0], VerbMatcher)
        assert matchers[0].verb == "sleep"


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestSleepCheck:
    def test_check_passes_for_fresh_actor(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_with_bedroom)
        result = mech.check(ctx)
        assert result.passed is True
        assert result.reasons == []

    def test_check_refuses_when_actor_missing(self, mech: SleepMechanic) -> None:
        kg = KnowledgeGraph()
        ctx = _ctx(kg, actor="ghost")
        result = mech.check(ctx)
        assert result.passed is False
        assert len(result.reasons) > 0

    def test_check_refuses_when_already_in_lra(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        """If current_long_action is a dict, refuse."""
        kg_with_bedroom.set(
            "alice",
            "current_long_action",
            {
                "action_text": "traveling",
                "turns_total": 3,
                "turns_elapsed": 1,
                "thresholds": [],
                "payload": {},
            },
        )
        ctx = _ctx(kg_with_bedroom)
        result = mech.check(ctx)
        assert result.passed is False
        assert len(result.reasons) > 0

    def test_check_passes_when_current_long_action_is_none(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        """None value for current_long_action is not an active LRA — pass."""
        kg_with_bedroom.set("alice", "current_long_action", None)
        ctx = _ctx(kg_with_bedroom)
        result = mech.check(ctx)
        assert result.passed is True

    def test_check_passes_when_current_long_action_absent(self, mech: SleepMechanic) -> None:
        """Property entirely absent — pass."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", health=0.9)
        ctx = _ctx(kg)
        result = mech.check(ctx)
        assert result.passed is True


# ---------------------------------------------------------------------------
# apply() — mutation order and shape
# ---------------------------------------------------------------------------


class TestSleepApplyMutations:
    def test_apply_returns_exactly_two_mutations(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_with_bedroom)
        mutations = mech.apply(ctx)
        assert len(mutations) == 2

    def test_apply_first_mutation_sets_is_sleeping(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_with_bedroom)
        mutations = mech.apply(ctx)
        m = mutations[0]
        assert m.target == "alice"
        assert m.property == "is_sleeping"
        assert m.new_value is True

    def test_apply_second_mutation_sets_current_long_action(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_with_bedroom)
        mutations = mech.apply(ctx)
        m = mutations[1]
        assert m.target == "alice"
        assert m.property == "current_long_action"

    def test_apply_sets_is_sleeping_in_graph(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_with_bedroom)
        mech.apply(ctx)
        assert kg_with_bedroom.query("alice", "is_sleeping") is True


# ---------------------------------------------------------------------------
# apply() — LRA shape: turns_total, action_text, thresholds, attention_state
# ---------------------------------------------------------------------------


class TestSleepApplyLra:
    def test_lra_action_text_is_sleeping(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_with_bedroom)
        mech.apply(ctx)
        lra = kg_with_bedroom.query("alice", "current_long_action")
        assert lra["action_text"] == "sleeping"

    def test_lra_turns_total_is_8(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_with_bedroom)
        mech.apply(ctx)
        lra = kg_with_bedroom.query("alice", "current_long_action")
        assert lra["turns_total"] == 8

    def test_lra_turns_elapsed_starts_at_0(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_with_bedroom)
        mech.apply(ctx)
        lra = kg_with_bedroom.query("alice", "current_long_action")
        assert lra["turns_elapsed"] == 0

    def test_lra_has_correct_attention_state(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_with_bedroom)
        mech.apply(ctx)
        lra = kg_with_bedroom.query("alice", "current_long_action")
        attn = lra["payload"]["attention_state"]
        assert attn == {
            "suppress": ["visual_detail", "smell"],
            "boost": ["noise_level"],
        }

    def test_lra_thresholds_with_location_include_noise_and_health(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_with_bedroom)
        mech.apply(ctx)
        lra = kg_with_bedroom.query("alice", "current_long_action")
        thresholds = lra["thresholds"]
        assert {"property": "bedroom.noise_level", "op": ">", "value": 0.7} in thresholds
        assert {"property": "alice.health", "op": "<", "value": 0.2} in thresholds

    def test_lra_noise_threshold_uses_room_id(
        self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        """Noise threshold property path starts with the room node ID."""
        ctx = _ctx(kg_with_bedroom)
        mech.apply(ctx)
        lra = kg_with_bedroom.query("alice", "current_long_action")
        noise_thresholds = [t for t in lra["thresholds"] if "noise_level" in t["property"]]
        assert len(noise_thresholds) == 1
        assert noise_thresholds[0]["property"] == "bedroom.noise_level"

    def test_full_lra_shape(self, kg_with_bedroom: KnowledgeGraph, mech: SleepMechanic) -> None:
        """Comprehensive test matching the spec sample exactly."""
        ctx = _ctx(kg_with_bedroom)
        mech.apply(ctx)
        lra = kg_with_bedroom.query("alice", "current_long_action")
        assert lra["action_text"] == "sleeping"
        assert lra["turns_total"] == 8
        assert lra["turns_elapsed"] == 0
        assert {"property": "bedroom.noise_level", "op": ">", "value": 0.7} in lra["thresholds"]
        assert {"property": "alice.health", "op": "<", "value": 0.2} in lra["thresholds"]
        assert lra["payload"]["attention_state"] == {
            "suppress": ["visual_detail", "smell"],
            "boost": ["noise_level"],
        }


# ---------------------------------------------------------------------------
# apply() — threshold fallback behaviour when no location
# ---------------------------------------------------------------------------


class TestSleepApplyFallback:
    def test_no_location_property_omits_noise_threshold(
        self, kg_no_location: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        """Actor with no location property: only health threshold, no crash."""
        ctx = _ctx(kg_no_location)
        # Must not raise
        mutations = mech.apply(ctx)
        assert len(mutations) == 2
        lra = kg_no_location.query("alice", "current_long_action")
        thresholds = lra["thresholds"]
        assert {"property": "alice.health", "op": "<", "value": 0.2} in thresholds
        # No noise threshold
        noise_props = [t for t in thresholds if "noise_level" in t["property"]]
        assert noise_props == []

    def test_ghost_room_location_omits_noise_threshold(
        self, kg_ghost_room: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        """Location property points to non-existent node: only health threshold."""
        ctx = _ctx(kg_ghost_room)
        mutations = mech.apply(ctx)
        assert len(mutations) == 2
        lra = kg_ghost_room.query("alice", "current_long_action")
        thresholds = lra["thresholds"]
        assert {"property": "alice.health", "op": "<", "value": 0.2} in thresholds
        noise_props = [t for t in thresholds if "noise_level" in t["property"]]
        assert noise_props == []

    def test_turns_total_is_exactly_8_without_location(
        self, kg_no_location: KnowledgeGraph, mech: SleepMechanic
    ) -> None:
        ctx = _ctx(kg_no_location)
        mech.apply(ctx)
        lra = kg_no_location.query("alice", "current_long_action")
        assert lra["turns_total"] == 8
