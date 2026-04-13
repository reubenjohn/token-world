"""Tests for MECH13 speak seed mechanic."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.speak import SpeakMechanic


@pytest.fixture
def uc_o08_graph() -> KnowledgeGraph:
    """UC-O08 shape: alice and bob in room_a; charlie in room_b beyond a wall."""
    kg = KnowledgeGraph()
    kg.add_node("alice", node_type="agent", position=[0, 0], last_utterance="help!")
    kg.add_node("bob", node_type="agent", position=[5, 0])
    kg.add_node("charlie", node_type="agent", position=[30, 0])
    kg.add_node(
        "room_a", node_type="entity", subtype="room", bbox=[-10, -10, 10, 10]
    )
    kg.add_node(
        "room_b", node_type="entity", subtype="room", bbox=[20, -10, 40, 10]
    )
    kg.add_node(
        "wall", node_type="entity", subtype="wall", blocks_sound=True
    )
    kg.add_edge("alice", "room_a", relation="located_in")
    kg.add_edge("bob", "room_a", relation="located_in")
    kg.add_edge("charlie", "room_b", relation="located_in")
    kg.add_edge("wall", "room_a", relation="borders")
    kg.add_edge("wall", "room_b", relation="borders")
    return kg


@pytest.fixture
def mechanic() -> SpeakMechanic:
    return SpeakMechanic()


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------


class TestSpeakMetadata:
    def test_id(self, mechanic: SpeakMechanic) -> None:
        assert mechanic.id == "speak"

    def test_voluntary(self, mechanic: SpeakMechanic) -> None:
        assert mechanic.voluntary is True

    def test_tags(self, mechanic: SpeakMechanic) -> None:
        for tag in ("social", "speech", "spatial"):
            assert tag in mechanic.tags


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestSpeakCheck:
    def test_passes_for_located_actor(
        self, uc_o08_graph: KnowledgeGraph, mechanic: SpeakMechanic
    ) -> None:
        ctx = MechanicContext(uc_o08_graph, actor="alice", target="alice")
        assert mechanic.check(ctx).passed is True

    def test_fails_when_actor_has_no_room(self, mechanic: SpeakMechanic) -> None:
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("located_in" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# apply() — UC-O08 partitioning
# ---------------------------------------------------------------------------


class TestSpeakApply:
    def test_uc_o08_same_room_listener_hears(
        self, uc_o08_graph: KnowledgeGraph, mechanic: SpeakMechanic
    ) -> None:
        """bob shares room_a with alice and is 5 units away — he hears."""
        ctx = MechanicContext(uc_o08_graph, actor="alice", target="alice")
        mechanic.apply(ctx)
        assert "help!" in uc_o08_graph.query("bob").get("last_heard", [])

    def test_uc_o08_different_room_listener_does_not_hear(
        self, uc_o08_graph: KnowledgeGraph, mechanic: SpeakMechanic
    ) -> None:
        """charlie is in room_b — must NOT receive the utterance."""
        ctx = MechanicContext(uc_o08_graph, actor="alice", target="alice")
        mechanic.apply(ctx)
        assert "last_heard" not in uc_o08_graph.query("charlie")

    def test_no_listeners_yields_no_mutations(
        self, mechanic: SpeakMechanic
    ) -> None:
        """Alone in the room → empty mutation list."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", last_utterance="hello")
        kg.add_node("room_a", node_type="entity", subtype="room")
        kg.add_edge("alice", "room_a", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        assert mechanic.apply(ctx) == []

    def test_earshot_radius_excludes_distant_same_room_listener(
        self, mechanic: SpeakMechanic
    ) -> None:
        """Listener in the same room but beyond earshot_radius isn't heard."""
        kg = KnowledgeGraph()
        kg.add_node(
            "alice",
            node_type="agent",
            position=[0, 0],
            last_utterance="hi",
            earshot_radius=5.0,
        )
        kg.add_node("eve", node_type="agent", position=[100, 100])  # out of earshot
        kg.add_node("hall", node_type="entity", subtype="room")
        kg.add_edge("alice", "hall", relation="located_in")
        kg.add_edge("eve", "hall", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        mechanic.apply(ctx)
        assert "last_heard" not in kg.query("eve")

    def test_last_heard_appends_to_existing_list(
        self, mechanic: SpeakMechanic
    ) -> None:
        """Second utterance appends; prior words are preserved."""
        kg = KnowledgeGraph()
        kg.add_node("alice", node_type="agent", last_utterance="two")
        kg.add_node("bob", node_type="agent", last_heard=["one"])
        kg.add_node("hall", node_type="entity", subtype="room")
        kg.add_edge("alice", "hall", relation="located_in")
        kg.add_edge("bob", "hall", relation="located_in")
        ctx = MechanicContext(kg, actor="alice", target="alice")
        mechanic.apply(ctx)
        assert kg.query("bob").get("last_heard") == ["one", "two"]
