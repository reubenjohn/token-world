"""Tests for KnowledgeGraph core operations."""

from __future__ import annotations

import pytest

from token_world.graph.knowledge_graph import KnowledgeGraph
from token_world.graph.models import Mutation

from .conftest import GraphBuilder


class TestAddNode:
    def test_add_node_agent(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        assert kg.has_node("bob")
        assert kg.query("bob", "type") == "agent"

    def test_add_node_entity(self, kg: KnowledgeGraph) -> None:
        kg.add_node("sword", node_type="entity")
        assert kg.has_node("sword")
        assert kg.query("sword", "type") == "entity"

    def test_add_node_requires_type(self, kg: KnowledgeGraph) -> None:
        with pytest.raises(TypeError):
            kg.add_node("bob")  # type: ignore[call-arg]

    def test_add_node_only_agent_or_entity(self, kg: KnowledgeGraph) -> None:
        with pytest.raises(ValueError, match="node_type must be"):
            kg.add_node("tavern", node_type="location")

    def test_arbitrary_properties(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent", hp=100, mood="happy")
        assert kg.query("bob", "hp") == 100
        assert kg.query("bob", "mood") == "happy"


class TestQuery:
    def test_query_node(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent", hp=100)
        result = kg.query("bob")
        assert result == {"type": "agent", "hp": 100}

    def test_query_node_property(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent", hp=100)
        assert kg.query("bob", "hp") == 100

    def test_query_missing_node(self, kg: KnowledgeGraph) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            kg.query("nonexistent")

    def test_has_node(self, kg: KnowledgeGraph) -> None:
        assert not kg.has_node("bob")
        kg.add_node("bob", node_type="agent")
        assert kg.has_node("bob")

    def test_has_edge(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        kg.add_node("sword", node_type="entity")
        assert not kg.has_edge("bob", "sword")
        kg.add_edge("bob", "sword", relation="holds")
        assert kg.has_edge("bob", "sword")

    def test_neighbors(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        kg.add_node("sword", node_type="entity")
        kg.add_node("shield", node_type="entity")
        kg.add_edge("bob", "sword")
        kg.add_edge("bob", "shield")
        neighbors = kg.neighbors("bob")
        assert sorted(neighbors) == ["shield", "sword"]

    def test_nodes_filter(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        kg.add_node("alice", node_type="agent")
        kg.add_node("sword", node_type="entity")
        agents = kg.nodes(type="agent")
        assert sorted(agents) == ["alice", "bob"]


class TestMutation:
    def test_set_property(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        kg.set("bob", "temperature", 98.6)
        assert kg.query("bob", "temperature") == 98.6

    def test_emergent_property(self, kg: KnowledgeGraph) -> None:
        """Any property name can be set without prior declaration."""
        kg.add_node("bob", node_type="agent")
        kg.set("bob", "completely_new_property_xyz", 42)
        assert kg.query("bob", "completely_new_property_xyz") == 42

    def test_mutation_return(self, kg: KnowledgeGraph) -> None:
        m = kg.add_node("bob", node_type="agent")
        assert isinstance(m, Mutation)
        assert m.type == "add_node"
        assert m.target == "bob"
        assert m.old_value is None
        assert m.new_value == {"type": "agent"}

    def test_set_returns_mutation_with_old_value(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent", hp=100)
        m = kg.set("bob", "hp", 80)
        assert m.type == "set_property"
        assert m.old_value == 100
        assert m.new_value == 80

    def test_deepcopy_mutable_values(self, kg: KnowledgeGraph) -> None:
        original = {"items": ["sword", "shield"]}
        kg.add_node("bob", node_type="agent", inventory=original)
        # Mutate the original dict
        original["items"].append("potion")
        # Graph should not be affected
        stored = kg.query("bob", "inventory")
        assert stored == {"items": ["sword", "shield"]}


class TestEdges:
    def test_add_edge(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        kg.add_node("sword", node_type="entity")
        m = kg.add_edge("bob", "sword", relation="holds")
        assert kg.has_edge("bob", "sword")
        assert m.type == "add_edge"
        assert m.target == "bob->sword"

    def test_edge_arbitrary_properties(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        kg.add_node("sword", node_type="entity")
        kg.add_edge("bob", "sword", relation="holds", strength=5, since="tick_0")
        # Verify edge data through NetworkX internals (query API is for nodes)
        assert kg._graph.edges["bob", "sword"]["relation"] == "holds"
        assert kg._graph.edges["bob", "sword"]["strength"] == 5


class TestRemove:
    def test_remove_node(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        kg.add_node("sword", node_type="entity")
        kg.add_edge("bob", "sword")
        kg.remove_node("bob")
        assert not kg.has_node("bob")
        assert not kg.has_edge("bob", "sword")

    def test_remove_edge(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        kg.add_node("sword", node_type="entity")
        kg.add_edge("bob", "sword")
        kg.remove_edge("bob", "sword")
        assert not kg.has_edge("bob", "sword")
        # Nodes still exist
        assert kg.has_node("bob")
        assert kg.has_node("sword")


class TestEventLogging:
    def test_event_logging(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        kg.set("bob", "hp", 100)
        events = kg._events.get_events()
        assert len(events) == 2
        assert events[0].event_type == "add_node"
        assert events[1].event_type == "set_property"


class TestPropertyValidation:
    def test_property_type_validation(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        with pytest.raises(TypeError, match="not allowed"):
            kg.set("bob", "x", set())  # type: ignore[arg-type]

    def test_allowed_types(self, kg: KnowledgeGraph) -> None:
        kg.add_node("bob", node_type="agent")
        # All these should succeed without error
        kg.set("bob", "s", "hello")
        kg.set("bob", "i", 42)
        kg.set("bob", "f", 3.14)
        kg.set("bob", "b", True)
        kg.set("bob", "n", None)
        kg.set("bob", "l", [1, 2, 3])
        kg.set("bob", "d", {"key": "value"})
        assert kg.query("bob", "s") == "hello"
        assert kg.query("bob", "i") == 42
        assert kg.query("bob", "f") == 3.14
        assert kg.query("bob", "b") is True
        assert kg.query("bob", "n") is None
        assert kg.query("bob", "l") == [1, 2, 3]
        assert kg.query("bob", "d") == {"key": "value"}


class TestGraphBuilder:
    def test_graph_builder(self, graph_builder: GraphBuilder) -> None:
        kg = (
            graph_builder
            .node("bob", node_type="agent", hp=100)
            .node("sword", node_type="entity")
            .edge("bob", "sword", relation="holds")
            .build()
        )
        assert kg.has_node("bob")
        assert kg.query("bob", "hp") == 100
        assert kg.has_node("sword")
        assert kg.has_edge("bob", "sword")

    def test_graph_builder_chaining(self) -> None:
        builder = GraphBuilder()
        result = builder.node("bob", node_type="agent")
        assert result is builder
        result = builder.edge("bob", "sword")
        assert result is builder
