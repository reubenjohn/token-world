"""Unit tests for the autopilot_advance passive seed mechanic (Plan 07-06, D-01, D-18).

Coverage:
- Class attributes: id, description, voluntary=False, tags
- watches() returns TickMatcher
- check() passes when a traveling actor exists; refuses when none
- apply() advances actor location by one room per tick
- apply() increments next_index in LRA payload
- apply() no-op when next_index is already at end of route
- apply() handles multiple traveling agents
- apply() ignores non-traveling LRAs (e.g. sleep)
- apply() ignores actors with no LRA
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.matchers import TickMatcher
from token_world.mechanic.seeds.autopilot_advance import AutopilotAdvanceMechanic

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TRAVEL_LRA = {
    "action_text": "traveling to room_d",
    "turns_total": 3,
    "turns_elapsed": 0,
    "thresholds": [],
    "payload": {
        "route": ["room_a", "room_b", "room_c", "room_d"],
        "next_index": 1,
        "attention_state": {"suppress": ["fine_detail"], "boost": ["hazard_level"]},
    },
}

_SLEEP_LRA = {
    "action_text": "sleeping",
    "turns_total": 8,
    "turns_elapsed": 0,
    "thresholds": [],
    "payload": {},
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mech() -> AutopilotAdvanceMechanic:
    return AutopilotAdvanceMechanic()


def _make_kg_with_traveler(
    route: list[str] | None = None,
    next_index: int = 1,
    actor_id: str = "alice",
    location: str = "room_a",
) -> KnowledgeGraph:
    """Graph with a single traveling agent and 4 linear rooms."""
    if route is None:
        route = ["room_a", "room_b", "room_c", "room_d"]
    kg = KnowledgeGraph()
    kg.add_node(actor_id, node_type="agent", location=location)
    for r in route:
        if not kg.has_node(r):
            kg.add_node(r, node_type="entity")
    lra = {
        "action_text": "traveling to room_d",
        "turns_total": len(route) - 1,
        "turns_elapsed": 0,
        "thresholds": [],
        "payload": {
            "route": list(route),
            "next_index": next_index,
            "attention_state": {"suppress": ["fine_detail"], "boost": ["hazard_level"]},
        },
    }
    kg.set(actor_id, "current_long_action", lra)
    return kg


def _sentinel_ctx(kg: KnowledgeGraph) -> MechanicContext:
    """Context simulating the passive-sweep sentinel actor pattern."""
    # The engine's passive sweep invokes involuntary mechanics with a sentinel
    # actor; the mechanic must iterate graph.nodes() to find real candidates.
    return MechanicContext(
        kg, actor="_sentinel", target="_sentinel", tick_id="tick_1", universe_seed=42
    )


# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


class TestAutopilotAdvanceClassAttrs:
    def test_id(self, mech: AutopilotAdvanceMechanic) -> None:
        assert mech.id == "autopilot_advance"

    def test_description_is_non_empty(self, mech: AutopilotAdvanceMechanic) -> None:
        assert isinstance(mech.description, str)
        assert len(mech.description) > 0

    def test_voluntary_is_false(self, mech: AutopilotAdvanceMechanic) -> None:
        """Involuntary passive mechanic (fires via TickMatcher on passive sweep)."""
        assert mech.voluntary is False

    def test_tags_contains_spatial(self, mech: AutopilotAdvanceMechanic) -> None:
        assert "spatial" in mech.tags

    def test_tags_contains_long_running(self, mech: AutopilotAdvanceMechanic) -> None:
        assert "long_running" in mech.tags

    def test_tags_contains_passive(self, mech: AutopilotAdvanceMechanic) -> None:
        assert "passive" in mech.tags


# ---------------------------------------------------------------------------
# watches()
# ---------------------------------------------------------------------------


class TestAutopilotAdvanceWatches:
    def test_watches_returns_tick_matcher(self, mech: AutopilotAdvanceMechanic) -> None:
        matchers = mech.watches()
        assert len(matchers) == 1
        assert isinstance(matchers[0], TickMatcher)


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestAutopilotAdvanceCheck:
    def test_check_refuses_when_no_traveling_actors(self, mech: AutopilotAdvanceMechanic) -> None:
        """Empty graph — no candidates → refuse."""
        kg = KnowledgeGraph()
        ctx = _sentinel_ctx(kg)
        result = mech.check(ctx)
        assert result.passed is False
        assert len(result.reasons) > 0

    def test_check_refuses_when_actor_has_no_lra(self, mech: AutopilotAdvanceMechanic) -> None:
        """Agent exists but has no LRA."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", location="room_a")
        ctx = _sentinel_ctx(kg)
        result = mech.check(ctx)
        assert result.passed is False

    def test_check_refuses_when_actor_sleeping_not_traveling(
        self, mech: AutopilotAdvanceMechanic
    ) -> None:
        """Agent with sleep LRA (not 'traveling') → refuse."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", location="room_a")
        kg.set("alice", "current_long_action", _SLEEP_LRA)
        ctx = _sentinel_ctx(kg)
        result = mech.check(ctx)
        assert result.passed is False

    def test_check_refuses_when_route_exhausted(self, mech: AutopilotAdvanceMechanic) -> None:
        """Traveling LRA but next_index >= len(route) → treated as no active traveler."""
        kg = _make_kg_with_traveler(route=["room_a", "room_b"], next_index=2)
        ctx = _sentinel_ctx(kg)
        result = mech.check(ctx)
        assert result.passed is False

    def test_check_passes_when_one_traveling_actor_exists(
        self, mech: AutopilotAdvanceMechanic
    ) -> None:
        kg = _make_kg_with_traveler()
        ctx = _sentinel_ctx(kg)
        result = mech.check(ctx)
        assert result.passed is True


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestAutopilotAdvanceApply:
    def test_apply_advances_actor_location_by_one_room(
        self, mech: AutopilotAdvanceMechanic
    ) -> None:
        """Alice starts in room_a (route[0]); after apply she should be in room_b (route[1])."""
        kg = _make_kg_with_traveler()
        ctx = _sentinel_ctx(kg)
        mech.apply(ctx)
        assert kg.query("alice", "location") == "room_b"

    def test_apply_increments_next_index_in_lra_payload(
        self, mech: AutopilotAdvanceMechanic
    ) -> None:
        """next_index must go from 1 → 2 after one advance."""
        kg = _make_kg_with_traveler()
        ctx = _sentinel_ctx(kg)
        mech.apply(ctx)
        lra = kg.query("alice", "current_long_action")
        assert lra["payload"]["next_index"] == 2

    def test_apply_no_op_when_next_index_at_end_of_route(
        self, mech: AutopilotAdvanceMechanic
    ) -> None:
        """Route=[r1,r2], next_index=2: no location mutation (route exhausted)."""
        kg = _make_kg_with_traveler(
            route=["room_a", "room_b"],
            next_index=2,
            location="room_b",
        )
        # Manually force next_index=2 even though check() would refuse (apply
        # can be called directly in tests to probe edge behaviour)
        ctx = _sentinel_ctx(kg)
        mutations = mech.apply(ctx)
        # No mutations should be returned — route is exhausted
        assert mutations == []
        # Location must not change
        assert kg.query("alice", "location") == "room_b"

    def test_apply_advances_multiple_travelers(self, mech: AutopilotAdvanceMechanic) -> None:
        """Two agents both traveling: both get advanced in one apply call."""
        kg = KnowledgeGraph()
        for name, start in [("alice", "room_a"), ("bob", "room_a")]:
            kg.add_node(name, node_type="agent", location=start)
        for r in ["room_a", "room_b", "room_c"]:
            kg.add_node(r, node_type="entity")

        lra_template = {
            "action_text": "traveling to room_c",
            "turns_total": 2,
            "turns_elapsed": 0,
            "thresholds": [],
            "payload": {
                "route": ["room_a", "room_b", "room_c"],
                "next_index": 1,
                "attention_state": {"suppress": ["fine_detail"], "boost": ["hazard_level"]},
            },
        }
        import copy

        kg.set("alice", "current_long_action", copy.deepcopy(lra_template))
        kg.set("bob", "current_long_action", copy.deepcopy(lra_template))

        ctx = _sentinel_ctx(kg)
        mech.apply(ctx)

        assert kg.query("alice", "location") == "room_b"
        assert kg.query("bob", "location") == "room_b"

    def test_apply_does_not_advance_non_traveling_actor(
        self, mech: AutopilotAdvanceMechanic
    ) -> None:
        """Agent with sleep LRA (not 'traveling') must not be advanced."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", location="room_a")
        kg.add_node("room_a", node_type="entity")
        kg.add_node("room_b", node_type="entity")
        kg.set("alice", "current_long_action", _SLEEP_LRA)

        ctx = _sentinel_ctx(kg)
        mutations = mech.apply(ctx)
        assert mutations == []
        assert kg.query("alice", "location") == "room_a"

    def test_apply_handles_actor_with_no_lra(self, mech: AutopilotAdvanceMechanic) -> None:
        """Agent with no LRA at all must be silently skipped."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", location="room_a")
        kg.add_node("room_a", node_type="entity")

        ctx = _sentinel_ctx(kg)
        mutations = mech.apply(ctx)
        assert mutations == []
        assert kg.query("alice", "location") == "room_a"

    def test_apply_route_preserved_in_lra(self, mech: AutopilotAdvanceMechanic) -> None:
        """The route list in payload must be unchanged after an advance."""
        route = ["room_a", "room_b", "room_c", "room_d"]
        kg = _make_kg_with_traveler(route=route)
        ctx = _sentinel_ctx(kg)
        mech.apply(ctx)
        lra = kg.query("alice", "current_long_action")
        assert lra["payload"]["route"] == route
