"""Unit tests for the autopilot_travel seed mechanic (Plan 07-06, D-01, D-13, D-18).

Coverage:
- Class attributes: id, description, voluntary, tags
- watches() returns VerbMatcher(verb='travel')
- check() passes/refuses for: missing actor, missing target, target==current location,
  already in LRA, no path, path exists
- apply() mutations: is_traveling=True, begin_long_action, augment with route+next_index
- apply() LRA shape: turns_total, action_text, thresholds per room, attention_state
- _find_path BFS helper: linear path, no path, max_depth cap
"""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.matchers import VerbMatcher
from token_world.mechanic.seeds.autopilot_travel import AutopilotTravelMechanic, _find_path

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mech() -> AutopilotTravelMechanic:
    return AutopilotTravelMechanic()


def _make_linear_kg() -> KnowledgeGraph:
    """4-room linear graph: room_a -- room_b -- room_c -- room_d (bidirectional edges).

    Alice is in room_a.
    """
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", location="room_a")
    kg.add_node("room_a", node_type="entity")
    kg.add_node("room_b", node_type="entity")
    kg.add_node("room_c", node_type="entity")
    kg.add_node("room_d", node_type="entity")
    # Bidirectional edges
    kg.add_edge("room_a", "room_b", relation="passage")
    kg.add_edge("room_b", "room_a", relation="passage")
    kg.add_edge("room_b", "room_c", relation="passage")
    kg.add_edge("room_c", "room_b", relation="passage")
    kg.add_edge("room_c", "room_d", relation="passage")
    kg.add_edge("room_d", "room_c", relation="passage")
    return kg


def _ctx(
    kg: KnowledgeGraph,
    actor: str = "alice",
    target: str = "room_d",
) -> MechanicContext:
    return MechanicContext(kg, actor=actor, target=target, tick_id="tick_1", universe_seed=42)


# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


class TestAutopilotTravelClassAttrs:
    def test_id(self, mech: AutopilotTravelMechanic) -> None:
        assert mech.id == "autopilot_travel"

    def test_description_is_non_empty(self, mech: AutopilotTravelMechanic) -> None:
        assert isinstance(mech.description, str)
        assert len(mech.description) > 0

    def test_voluntary_is_true(self, mech: AutopilotTravelMechanic) -> None:
        assert mech.voluntary is True

    def test_tags_contains_spatial(self, mech: AutopilotTravelMechanic) -> None:
        assert "spatial" in mech.tags

    def test_tags_contains_long_running(self, mech: AutopilotTravelMechanic) -> None:
        assert "long_running" in mech.tags


# ---------------------------------------------------------------------------
# watches()
# ---------------------------------------------------------------------------


class TestAutopilotTravelWatches:
    def test_watches_returns_verb_matcher_travel(self, mech: AutopilotTravelMechanic) -> None:
        matchers = mech.watches()
        assert len(matchers) == 1
        assert isinstance(matchers[0], VerbMatcher)
        assert matchers[0].verb == "travel"


# ---------------------------------------------------------------------------
# check() — refusal cases
# ---------------------------------------------------------------------------


class TestAutopilotTravelCheck:
    def test_check_refuses_when_no_actor(self, mech: AutopilotTravelMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("room_a", node_type="entity")
        ctx = MechanicContext(kg, actor="ghost", target="room_a", tick_id="t1", universe_seed=42)
        result = mech.check(ctx)
        assert result.passed is False
        assert len(result.reasons) > 0

    def test_check_refuses_when_no_target(self, mech: AutopilotTravelMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", location="room_a")
        kg.add_node("room_a", node_type="entity")
        ctx = MechanicContext(
            kg, actor="alice", target="nonexistent", tick_id="t1", universe_seed=42
        )
        result = mech.check(ctx)
        assert result.passed is False

    def test_check_refuses_when_target_is_current_location(
        self, mech: AutopilotTravelMechanic
    ) -> None:
        """Actor already at target: no travel needed."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", location="room_a")
        kg.add_node("room_a", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="room_a", tick_id="t1", universe_seed=42)
        result = mech.check(ctx)
        assert result.passed is False

    def test_check_refuses_when_already_in_lra(self, mech: AutopilotTravelMechanic) -> None:
        """Actor already has an active LRA: single active per agent (D-04)."""
        kg = _make_linear_kg()
        kg.set(
            "alice",
            "current_long_action",
            {
                "action_text": "sleeping",
                "turns_total": 8,
                "turns_elapsed": 2,
                "thresholds": [],
                "payload": {},
            },
        )
        ctx = _ctx(kg)
        result = mech.check(ctx)
        assert result.passed is False

    def test_check_refuses_when_no_path(self, mech: AutopilotTravelMechanic) -> None:
        """Disconnected graph: room_x is isolated; no path from room_a."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", location="room_a")
        kg.add_node("room_a", node_type="entity")
        kg.add_node("room_x", node_type="entity")  # isolated — no edges
        ctx = MechanicContext(kg, actor="alice", target="room_x", tick_id="t1", universe_seed=42)
        result = mech.check(ctx)
        assert result.passed is False

    def test_check_passes_when_path_exists(self, mech: AutopilotTravelMechanic) -> None:
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        result = mech.check(ctx)
        assert result.passed is True


# ---------------------------------------------------------------------------
# apply() — mutations
# ---------------------------------------------------------------------------


class TestAutopilotTravelApply:
    def test_apply_sets_is_traveling_true(self, mech: AutopilotTravelMechanic) -> None:
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        mech.apply(ctx)
        assert kg.query("alice", "is_traveling") is True

    def test_apply_begin_long_action_turns_total_equals_path_length_minus_one(
        self, mech: AutopilotTravelMechanic
    ) -> None:
        """4 rooms → turns_total = 3 (3 hops to traverse)."""
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        mech.apply(ctx)
        lra = kg.query("alice", "current_long_action")
        # path = [room_a, room_b, room_c, room_d] → len=4 → turns_total=3
        assert lra["turns_total"] == 3

    def test_apply_lra_payload_route_is_full_path_list(self, mech: AutopilotTravelMechanic) -> None:
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        mech.apply(ctx)
        lra = kg.query("alice", "current_long_action")
        route = lra["payload"]["route"]
        assert route == ["room_a", "room_b", "room_c", "room_d"]

    def test_apply_lra_payload_next_index_is_1(self, mech: AutopilotTravelMechanic) -> None:
        """next_index starts at 1 (first advance moves route[0]→route[1])."""
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        mech.apply(ctx)
        lra = kg.query("alice", "current_long_action")
        assert lra["payload"]["next_index"] == 1

    def test_apply_lra_attention_state_exact(self, mech: AutopilotTravelMechanic) -> None:
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        mech.apply(ctx)
        lra = kg.query("alice", "current_long_action")
        attn = lra["payload"]["attention_state"]
        assert attn == {
            "suppress": ["fine_detail"],
            "boost": ["hazard_level"],
        }

    def test_apply_lra_thresholds_include_hazard_for_each_room(
        self, mech: AutopilotTravelMechanic
    ) -> None:
        """Thresholds: one per room in route (4 rooms → 4 thresholds)."""
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        mech.apply(ctx)
        lra = kg.query("alice", "current_long_action")
        thresholds = lra["thresholds"]
        # All 4 rooms should have hazard_level thresholds
        for room in ["room_a", "room_b", "room_c", "room_d"]:
            expected = {"property": f"{room}.hazard_level", "op": ">", "value": 0.5}
            assert expected in thresholds, f"Missing threshold for {room}: {thresholds}"

    def test_apply_action_text_contains_target(self, mech: AutopilotTravelMechanic) -> None:
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        mech.apply(ctx)
        lra = kg.query("alice", "current_long_action")
        assert "traveling to" in lra["action_text"]
        assert "room_d" in lra["action_text"]

    def test_apply_lra_turns_elapsed_starts_at_zero(self, mech: AutopilotTravelMechanic) -> None:
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        mech.apply(ctx)
        lra = kg.query("alice", "current_long_action")
        assert lra["turns_elapsed"] == 0

    def test_apply_returns_three_mutations(self, mech: AutopilotTravelMechanic) -> None:
        """apply() returns: set(is_traveling), begin_long_action, augment(current_long_action)."""
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        mutations = mech.apply(ctx)
        assert len(mutations) == 3


# ---------------------------------------------------------------------------
# _find_path BFS helper — unit-tested directly (pure function)
# ---------------------------------------------------------------------------


class TestFindPathBfs:
    def test_find_path_bfs_linear(self) -> None:
        """4 linear rooms → shortest path = [room_a, room_b, room_c, room_d]."""
        kg = _make_linear_kg()
        ctx = MechanicContext(kg, actor="alice", target="room_d", tick_id="t1", universe_seed=42)
        result = _find_path(ctx, "room_a", "room_d")
        assert result == ["room_a", "room_b", "room_c", "room_d"]

    def test_find_path_bfs_same_node(self) -> None:
        """BFS with start == end returns single-element list."""
        kg = _make_linear_kg()
        ctx = MechanicContext(kg, actor="alice", target="room_a", tick_id="t1", universe_seed=42)
        result = _find_path(ctx, "room_a", "room_a")
        assert result == ["room_a"]

    def test_find_path_bfs_no_path_returns_none(self) -> None:
        """Isolated node: no path → None."""
        kg = KnowledgeGraph()
        kg.add_node("room_a", node_type="entity")
        kg.add_node("room_x", node_type="entity")
        ctx = MechanicContext(kg, actor="room_a", target="room_x", tick_id="t1", universe_seed=42)
        result = _find_path(ctx, "room_a", "room_x")
        assert result is None

    def test_find_path_bfs_respects_max_depth_cap(self) -> None:
        """Chain of 5 rooms: if max_depth=3, cannot reach the 5th room → None."""
        kg = KnowledgeGraph()
        rooms = [f"room_{i}" for i in range(5)]
        for r in rooms:
            kg.add_node(r, node_type="entity")
        for i in range(len(rooms) - 1):
            kg.add_edge(rooms[i], rooms[i + 1], relation="passage")
        ctx = MechanicContext(kg, actor=rooms[0], target=rooms[4], tick_id="t1", universe_seed=42)
        # max_depth=3 means path can be at most 3 nodes long; rooms[0]→rooms[4] needs 5
        result = _find_path(ctx, rooms[0], rooms[4], max_depth=3)
        assert result is None

    def test_find_path_bfs_missing_start_node_returns_none(self) -> None:
        """BFS with nonexistent start → None, no crash."""
        kg = KnowledgeGraph()
        kg.add_node("room_a", node_type="entity")
        ctx = MechanicContext(kg, actor="ghost", target="room_a", tick_id="t1", universe_seed=42)
        result = _find_path(ctx, "ghost", "room_a")
        assert result is None

    def test_find_path_bfs_missing_end_node_returns_none(self) -> None:
        """BFS with nonexistent end → None, no crash."""
        kg = KnowledgeGraph()
        kg.add_node("room_a", node_type="entity")
        ctx = MechanicContext(kg, actor="room_a", target="ghost", tick_id="t1", universe_seed=42)
        result = _find_path(ctx, "room_a", "ghost")
        assert result is None


# ---------------------------------------------------------------------------
# WR-02: apply() returns [] when path resolves to None or len < 2 (no assert)
# ---------------------------------------------------------------------------


class TestAutopilotTravelApplyGuard:
    def test_apply_returns_empty_list_when_path_is_none(
        self, mech: AutopilotTravelMechanic
    ) -> None:
        """apply() must return [] gracefully when _find_path returns None (WR-02).

        We simulate the failure by removing the room nodes after check() passes
        but before apply() would run — i.e., by calling apply() directly on a
        context where the graph no longer has a valid path.
        """
        kg = KnowledgeGraph()
        # Actor with a location property that exists but has no outgoing edges to target
        kg.add_node("alice", node_type="agent", location="room_a")
        kg.add_node("room_a", node_type="entity")
        kg.add_node("room_d", node_type="entity")
        # No edges — BFS returns None
        ctx = MechanicContext(kg, actor="alice", target="room_d", tick_id="t1", universe_seed=42)
        result = mech.apply(ctx)
        assert result == []

    def test_apply_returns_empty_list_when_path_is_single_node(
        self, mech: AutopilotTravelMechanic
    ) -> None:
        """apply() must return [] when path has only one node (start == end) (WR-02)."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", location="room_a")
        kg.add_node("room_a", node_type="entity")
        # Target is the same as location — _find_path returns ["room_a"] (len=1)
        ctx = MechanicContext(kg, actor="alice", target="room_a", tick_id="t1", universe_seed=42)
        result = mech.apply(ctx)
        assert result == []

    def test_apply_does_not_raise_when_path_is_none(self, mech: AutopilotTravelMechanic) -> None:
        """No AssertionError or AttributeError when path is None (WR-02)."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", location="room_a")
        kg.add_node("room_a", node_type="entity")
        kg.add_node("room_d", node_type="entity")
        ctx = MechanicContext(kg, actor="alice", target="room_d", tick_id="t1", universe_seed=42)
        # Must not raise
        try:
            mech.apply(ctx)
        except (AssertionError, AttributeError) as exc:
            raise AssertionError(f"apply() raised {type(exc).__name__}: {exc}") from exc


# ---------------------------------------------------------------------------
# WR-01: apply() stores clear_on_end={"is_traveling": False} in LRA payload
# ---------------------------------------------------------------------------


class TestAutopilotTravelClearOnEnd:
    def test_apply_stores_clear_on_end_in_lra_payload(self, mech: AutopilotTravelMechanic) -> None:
        """apply() must include clear_on_end={"is_traveling": False} in the LRA payload."""
        kg = _make_linear_kg()
        ctx = _ctx(kg)
        mech.apply(ctx)
        lra = kg.query("alice", "current_long_action")
        assert "clear_on_end" in lra["payload"]
        assert lra["payload"]["clear_on_end"] == {"is_traveling": False}
