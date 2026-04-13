"""Tests for MechanicContext.begin_long_action() helper (07-03, D-05, D-15).

Tests cover:
- Helper writes current_long_action to actor node
- Exact stored dict shape (canonical on-graph schema)
- turns_total=None preserved (indefinite actions, D-16)
- attention_state=None yields empty payload
- attention_state provided lives under payload.attention_state (D-12)
- Empty thresholds list stored as []
- Returns a Mutation with kind="set_property" (D-05: stays within list[Mutation] protocol)
- Overwrites existing current_long_action (D-04: single active action per agent)
- JSON round-trip through graph storage (ALLOWED_PROPERTY_TYPES verification)
- Thresholds defensive copy (mutation of caller's list does not affect stored value)
- Writes to actor, not target
"""

from __future__ import annotations

import json

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def kg() -> KnowledgeGraph:
    """In-memory KnowledgeGraph for begin_long_action tests."""
    graph = KnowledgeGraph(db_path=None)
    graph.add_node("alice", node_type="agent")
    graph.add_node("bedroom", node_type="entity", noise_level=0.1)
    return graph


@pytest.fixture
def ctx(kg: KnowledgeGraph) -> MechanicContext:
    """MechanicContext with alice as actor and bedroom as target."""
    return MechanicContext(kg, actor="alice", target="bedroom")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBeginLongActionWritesToActorNode:
    """begin_long_action writes current_long_action to ctx.actor."""

    def test_begin_long_action_writes_to_actor_node(
        self, ctx: MechanicContext, kg: KnowledgeGraph
    ) -> None:
        mutation = ctx.begin_long_action(
            action_text="sleeping",
            turns_total=8,
            thresholds=[{"property": "bedroom.noise_level", "op": ">", "value": 0.7}],
            attention_state={"suppress": ["visual_detail"]},
        )
        stored = kg.query("alice", "current_long_action")
        assert stored["action_text"] == "sleeping"
        assert stored["turns_total"] == 8
        assert stored["turns_elapsed"] == 0
        assert stored["thresholds"] == [
            {"property": "bedroom.noise_level", "op": ">", "value": 0.7}
        ]
        assert stored["payload"] == {"attention_state": {"suppress": ["visual_detail"]}}
        assert mutation.target == "alice"
        assert mutation.property == "current_long_action"

    def test_turns_total_none_stored_as_none(
        self, ctx: MechanicContext, kg: KnowledgeGraph
    ) -> None:
        """turns_total=None is preserved — indefinite action (D-16)."""
        ctx.begin_long_action(
            action_text="drunk",
            turns_total=None,
            thresholds=[],
        )
        stored = kg.query("alice", "current_long_action")
        assert stored["turns_total"] is None

    def test_attention_state_none_yields_empty_payload(
        self, ctx: MechanicContext, kg: KnowledgeGraph
    ) -> None:
        """attention_state=None results in payload={} (not missing key)."""
        ctx.begin_long_action(
            action_text="traveling",
            turns_total=5,
            thresholds=[],
            attention_state=None,
        )
        stored = kg.query("alice", "current_long_action")
        assert "payload" in stored
        assert stored["payload"] == {}

    def test_empty_thresholds_list_stored(self, ctx: MechanicContext, kg: KnowledgeGraph) -> None:
        """thresholds=[] stores as [] — no thresholds, action runs to completion."""
        ctx.begin_long_action(
            action_text="meditating",
            turns_total=3,
            thresholds=[],
        )
        stored = kg.query("alice", "current_long_action")
        assert stored["thresholds"] == []

    def test_returns_mutation_with_set_property_kind(self, ctx: MechanicContext) -> None:
        """Return value is a Mutation with kind/type matching 'set_property'."""
        mutation = ctx.begin_long_action(
            action_text="sleeping",
            turns_total=8,
            thresholds=[],
        )
        # Mutation may use `.kind` or `.type` depending on implementation.
        # Check the one that's populated (set_property is the canonical value).
        kind_val = getattr(mutation, "kind", None) or getattr(mutation, "type", None)
        assert kind_val == "set_property"

    def test_overwrites_existing_current_long_action(
        self, ctx: MechanicContext, kg: KnowledgeGraph
    ) -> None:
        """Second begin_long_action overwrites first (D-04: single active action)."""
        ctx.begin_long_action(action_text="sleeping", turns_total=8, thresholds=[])
        first_stored = kg.query("alice", "current_long_action")

        second_mutation = ctx.begin_long_action(
            action_text="daydreaming",
            turns_total=3,
            thresholds=[],
        )
        # old_value of second mutation should equal first stored dict
        assert second_mutation.old_value == first_stored
        # Final stored value is the second call's dict
        final = kg.query("alice", "current_long_action")
        assert final["action_text"] == "daydreaming"
        assert final["turns_total"] == 3

    def test_json_round_trip_through_graph_storage(
        self, ctx: MechanicContext, kg: KnowledgeGraph
    ) -> None:
        """Stored value round-trips through json.dumps/loads (ALLOWED_PROPERTY_TYPES)."""
        ctx.begin_long_action(
            action_text="sleeping",
            turns_total=8,
            thresholds=[{"property": "bedroom.noise_level", "op": ">", "value": 0.7}],
            attention_state={"suppress": ["visual_detail"], "boost": ["noise_level"]},
        )
        stored = kg.query("alice", "current_long_action")
        round_tripped = json.loads(json.dumps(stored))
        assert round_tripped == stored

    def test_thresholds_defensive_copy(self, ctx: MechanicContext, kg: KnowledgeGraph) -> None:
        """Mutating the caller's thresholds list after the call does not affect stored value."""
        thresholds = [{"property": "bedroom.noise_level", "op": ">", "value": 0.7}]
        ctx.begin_long_action(
            action_text="sleeping",
            turns_total=8,
            thresholds=thresholds,
        )
        # Mutate the original list
        thresholds.append({"property": "bedroom.temp", "op": ">", "value": 30.0})
        stored = kg.query("alice", "current_long_action")
        # Only the original threshold should be in the stored value
        assert len(stored["thresholds"]) == 1
        assert stored["thresholds"][0]["property"] == "bedroom.noise_level"

    def test_writes_to_actor_not_target(self, ctx: MechanicContext, kg: KnowledgeGraph) -> None:
        """begin_long_action writes to ctx.actor, not ctx.target (D-02)."""
        ctx.begin_long_action(
            action_text="sleeping",
            turns_total=8,
            thresholds=[],
        )
        # actor (alice) has current_long_action
        alice_lra = kg.query("alice", "current_long_action")
        assert alice_lra is not None
        assert alice_lra["action_text"] == "sleeping"
        # target (bedroom) does NOT have current_long_action — property absent
        bedroom_props = kg.query("bedroom")
        assert "current_long_action" not in bedroom_props

    def test_attention_state_lives_under_payload_attention_state(
        self, ctx: MechanicContext, kg: KnowledgeGraph
    ) -> None:
        """attention_state dict is nested under payload['attention_state'] (D-12)."""
        attention = {"suppress": ["visual_detail", "smell"], "boost": ["noise_level"]}
        ctx.begin_long_action(
            action_text="sleeping",
            turns_total=8,
            thresholds=[],
            attention_state=attention,
        )
        stored = kg.query("alice", "current_long_action")
        assert stored["payload"]["attention_state"] == attention

    def test_turns_elapsed_always_starts_at_zero(
        self, ctx: MechanicContext, kg: KnowledgeGraph
    ) -> None:
        """turns_elapsed is always 0 on creation; the engine hook advances it (Plan 04)."""
        ctx.begin_long_action(
            action_text="traveling",
            turns_total=10,
            thresholds=[],
        )
        stored = kg.query("alice", "current_long_action")
        assert stored["turns_elapsed"] == 0
