"""Tests for the observation seed mechanic."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.context import MechanicContext
from token_world.mechanic.seeds.observation.mechanic import ObservationMechanic


@pytest.fixture
def observation_graph() -> KnowledgeGraph:
    """Graph with an agent that has a location."""
    kg = KnowledgeGraph()
    kg.add_node("room_a", node_type="entity")
    kg.add_node("alice", node_type="agent", location="room_a")
    kg.add_node("rock", node_type="entity", location="room_a")
    return kg


@pytest.fixture
def mechanic() -> ObservationMechanic:
    return ObservationMechanic()


class TestObservationCheck:
    def test_check_passes_with_location(
        self, observation_graph: KnowledgeGraph, mechanic: ObservationMechanic
    ) -> None:
        ctx = MechanicContext(observation_graph, actor="alice", target="room_a")
        result = mechanic.check(ctx)
        assert result.passed is True

    def test_check_fails_no_location(
        self, observation_graph: KnowledgeGraph, mechanic: ObservationMechanic
    ) -> None:
        observation_graph.add_node("bob", node_type="agent")
        ctx = MechanicContext(observation_graph, actor="bob", target="room_a")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("has no location" in r for r in result.reasons)

    def test_check_fails_actor_missing(self, mechanic: ObservationMechanic) -> None:
        kg = KnowledgeGraph()
        ctx = MechanicContext(kg, actor="ghost", target="room_a")
        result = mechanic.check(ctx)
        assert result.passed is False
        assert any("does not exist" in r for r in result.reasons)


class TestObservationApply:
    def test_apply_returns_empty(
        self, observation_graph: KnowledgeGraph, mechanic: ObservationMechanic
    ) -> None:
        ctx = MechanicContext(observation_graph, actor="alice", target="room_a")
        result = mechanic.apply(ctx)
        assert result == []


class TestObservationProperties:
    def test_observation_is_voluntary(self, mechanic: ObservationMechanic) -> None:
        assert mechanic.voluntary is True

    def test_watches_returns_empty(self, mechanic: ObservationMechanic) -> None:
        assert mechanic.watches() == []

    def test_id(self, mechanic: ObservationMechanic) -> None:
        assert mechanic.id == "observation"
