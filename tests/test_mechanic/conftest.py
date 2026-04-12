"""Test fixtures for mechanic framework tests."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph, Mutation
from token_world.mechanic import CheckResult, Mechanic, MechanicContext


class DummyMechanic(Mechanic):
    """Concrete mechanic for testing. Always passes, sets 'tested' property."""

    id = "dummy"
    description = "test mechanic"

    def check(self, ctx: MechanicContext) -> CheckResult:
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return [ctx.mutate(ctx.actor, "tested", True)]


class FailingMechanic(Mechanic):
    """Mechanic that always fails its check."""

    id = "failing"
    description = "always fails"

    def check(self, ctx: MechanicContext) -> CheckResult:
        return CheckResult(passed=False, reasons=["always fails"])

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        return []


@pytest.fixture
def mechanic_graph() -> KnowledgeGraph:
    """A graph with rooms, an agent, and an entity for mechanic testing."""
    kg = KnowledgeGraph()
    kg.add_node("room_a", node_type="entity", location=True)
    kg.add_node("room_b", node_type="entity", location=True)
    kg.add_node("alice", node_type="agent", location="room_a")
    kg.add_node("rock", node_type="entity", location="room_a")
    kg.add_edge("room_a", "room_b", relation="path")
    kg.add_edge("room_b", "room_a", relation="path")
    return kg


@pytest.fixture
def mechanic_ctx(mechanic_graph: KnowledgeGraph) -> MechanicContext:
    """A MechanicContext with alice as actor and room_b as target."""
    return MechanicContext(mechanic_graph, actor="alice", target="room_b")
