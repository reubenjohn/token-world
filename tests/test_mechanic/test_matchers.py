"""Tests for declarative matcher primitives."""

from __future__ import annotations

import pytest

from token_world.graph import KnowledgeGraph, Mutation
from token_world.mechanic import EdgeMatcher, NodeMatcher, PropertyChangeMatcher
from token_world.mechanic.matchers import matches


@pytest.fixture
def simple_graph() -> KnowledgeGraph:
    """A simple graph for matcher tests."""
    kg = KnowledgeGraph()
    kg.add_node("node1", node_type="entity", temperature=100)
    kg.add_node("agent1", node_type="agent", health=50)
    return kg


class TestPropertyChangeMatcher:
    """Tests for PropertyChangeMatcher."""

    def test_matches_correct_property(self, simple_graph: KnowledgeGraph) -> None:
        """Matches set_property mutation with correct property name."""
        matcher = PropertyChangeMatcher(property_name="temperature")
        mutation = Mutation(
            type="set_property",
            target="node1",
            property="temperature",
            old_value=20,
            new_value=100,
        )
        assert matches(matcher, mutation, simple_graph) is True

    def test_no_match_wrong_property(self, simple_graph: KnowledgeGraph) -> None:
        """Does not match wrong property name."""
        matcher = PropertyChangeMatcher(property_name="health")
        mutation = Mutation(
            type="set_property",
            target="node1",
            property="temperature",
            old_value=20,
            new_value=100,
        )
        assert matches(matcher, mutation, simple_graph) is False

    def test_no_match_wrong_mutation_type(self, simple_graph: KnowledgeGraph) -> None:
        """Does not match non-set_property mutations."""
        matcher = PropertyChangeMatcher(property_name="temperature")
        mutation = Mutation(
            type="add_node",
            target="node1",
            property=None,
            old_value=None,
            new_value={"type": "entity"},
        )
        assert matches(matcher, mutation, simple_graph) is False

    def test_node_type_filter_matches(self, simple_graph: KnowledgeGraph) -> None:
        """With node_type filter, matches if target node has that type."""
        matcher = PropertyChangeMatcher(property_name="temperature", node_type="entity")
        mutation = Mutation(
            type="set_property",
            target="node1",
            property="temperature",
            old_value=20,
            new_value=100,
        )
        assert matches(matcher, mutation, simple_graph) is True

    def test_node_type_filter_rejects(self, simple_graph: KnowledgeGraph) -> None:
        """With node_type filter, rejects if target node has wrong type."""
        matcher = PropertyChangeMatcher(property_name="health", node_type="entity")
        mutation = Mutation(
            type="set_property",
            target="agent1",
            property="health",
            old_value=100,
            new_value=50,
        )
        assert matches(matcher, mutation, simple_graph) is False

    def test_node_type_filter_missing_node(self, simple_graph: KnowledgeGraph) -> None:
        """With node_type filter, rejects if target node doesn't exist."""
        matcher = PropertyChangeMatcher(property_name="x", node_type="entity")
        mutation = Mutation(
            type="set_property",
            target="nonexistent",
            property="x",
            old_value=None,
            new_value=1,
        )
        assert matches(matcher, mutation, simple_graph) is False


class TestEdgeMatcher:
    """Tests for EdgeMatcher."""

    def test_matches_add_edge(self, simple_graph: KnowledgeGraph) -> None:
        """Matches add_edge mutation."""
        matcher = EdgeMatcher(event_type="add_edge")
        mutation = Mutation(
            type="add_edge",
            target="node1->agent1",
            property=None,
            old_value=None,
            new_value={"relation": "near"},
        )
        assert matches(matcher, mutation, simple_graph) is True

    def test_no_match_wrong_event_type(self, simple_graph: KnowledgeGraph) -> None:
        """Does not match remove_edge when expecting add_edge."""
        matcher = EdgeMatcher(event_type="add_edge")
        mutation = Mutation(
            type="remove_edge",
            target="node1->agent1",
            property=None,
            old_value=None,
            new_value=None,
        )
        assert matches(matcher, mutation, simple_graph) is False

    def test_invalid_event_type_raises(self) -> None:
        """Invalid event_type raises ValueError."""
        with pytest.raises(ValueError, match="add_edge.*remove_edge"):
            EdgeMatcher(event_type="set_property")

    def test_matches_remove_edge(self, simple_graph: KnowledgeGraph) -> None:
        """Matches remove_edge mutation."""
        matcher = EdgeMatcher(event_type="remove_edge")
        mutation = Mutation(
            type="remove_edge",
            target="node1->agent1",
            property=None,
            old_value={"relation": "near"},
            new_value=None,
        )
        assert matches(matcher, mutation, simple_graph) is True


class TestNodeMatcher:
    """Tests for NodeMatcher."""

    def test_matches_add_node(self, simple_graph: KnowledgeGraph) -> None:
        """Matches add_node mutation."""
        matcher = NodeMatcher(event_type="add_node")
        mutation = Mutation(
            type="add_node",
            target="new_node",
            property=None,
            old_value=None,
            new_value={"type": "entity"},
        )
        assert matches(matcher, mutation, simple_graph) is True

    def test_matches_remove_node(self, simple_graph: KnowledgeGraph) -> None:
        """Matches remove_node mutation."""
        matcher = NodeMatcher(event_type="remove_node")
        mutation = Mutation(
            type="remove_node",
            target="old_node",
            property=None,
            old_value={"type": "entity"},
            new_value=None,
        )
        assert matches(matcher, mutation, simple_graph) is True

    def test_node_type_filter_matches(self, simple_graph: KnowledgeGraph) -> None:
        """With node_type filter, matches if new_value has matching type."""
        matcher = NodeMatcher(event_type="add_node", node_type="agent")
        mutation = Mutation(
            type="add_node",
            target="bob",
            property=None,
            old_value=None,
            new_value={"type": "agent"},
        )
        assert matches(matcher, mutation, simple_graph) is True

    def test_node_type_filter_rejects(self, simple_graph: KnowledgeGraph) -> None:
        """With node_type filter, rejects if type doesn't match."""
        matcher = NodeMatcher(event_type="add_node", node_type="agent")
        mutation = Mutation(
            type="add_node",
            target="rock",
            property=None,
            old_value=None,
            new_value={"type": "entity"},
        )
        assert matches(matcher, mutation, simple_graph) is False

    def test_invalid_event_type_raises(self) -> None:
        """Invalid event_type raises ValueError."""
        with pytest.raises(ValueError, match="add_node.*remove_node"):
            NodeMatcher(event_type="set_property")
