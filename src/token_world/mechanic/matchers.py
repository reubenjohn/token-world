"""Declarative matcher primitives for involuntary mechanic triggering."""

from __future__ import annotations

from dataclasses import dataclass

from token_world.graph import KnowledgeGraph, Mutation


@dataclass(frozen=True)
class PropertyChangeMatcher:
    """Matches mutations that set a specific property.

    Attributes:
        property_name: The property name to watch for changes.
        node_type: If set, only match if the target node has this type
            (e.g. "agent" or "entity").
    """

    property_name: str
    node_type: str | None = None


@dataclass(frozen=True)
class EdgeMatcher:
    """Matches edge addition or removal mutations.

    Attributes:
        event_type: Must be "add_edge" or "remove_edge".
        edge_label: If set, only match edges with this label in their properties.
    """

    event_type: str
    edge_label: str | None = None

    def __post_init__(self) -> None:
        if self.event_type not in ("add_edge", "remove_edge"):
            raise ValueError(
                f"EdgeMatcher event_type must be 'add_edge' or 'remove_edge', "
                f"got '{self.event_type}'"
            )


@dataclass(frozen=True)
class NodeMatcher:
    """Matches node addition or removal mutations.

    Attributes:
        event_type: Must be "add_node" or "remove_node".
        node_type: If set, only match nodes with this type.
    """

    event_type: str
    node_type: str | None = None

    def __post_init__(self) -> None:
        if self.event_type not in ("add_node", "remove_node"):
            raise ValueError(
                f"NodeMatcher event_type must be 'add_node' or 'remove_node', "
                f"got '{self.event_type}'"
            )


Matcher = PropertyChangeMatcher | EdgeMatcher | NodeMatcher
"""Union type for all matcher primitives."""


def matches(matcher: Matcher, mutation: Mutation, graph: KnowledgeGraph) -> bool:
    """Evaluate whether a matcher matches a given mutation.

    Args:
        matcher: The matcher to evaluate.
        mutation: The mutation to test against.
        graph: The knowledge graph (needed for node_type lookups).

    Returns:
        True if the matcher matches the mutation.
    """
    if isinstance(matcher, PropertyChangeMatcher):
        if mutation.type != "set_property":
            return False
        if mutation.property != matcher.property_name:
            return False
        if matcher.node_type is not None:
            # Check target node's type in the graph
            if not graph.has_node(mutation.target):
                return False
            node_props = graph.query(mutation.target)
            if node_props.get("type") != matcher.node_type:
                return False
        return True

    if isinstance(matcher, EdgeMatcher):
        if mutation.type != matcher.event_type:
            return False
        if matcher.edge_label is not None:
            # Edge properties are stored in new_value (add) or old_value (remove)
            props = mutation.new_value or mutation.old_value
            if not isinstance(props, dict) or props.get("relation") != matcher.edge_label:
                return False
        return True

    if isinstance(matcher, NodeMatcher):
        if mutation.type != matcher.event_type:
            return False
        if matcher.node_type is not None:
            # For add_node, new_value is a dict with "type" key
            if mutation.type == "add_node":
                if not isinstance(mutation.new_value, dict):
                    return False
                if mutation.new_value.get("type") != matcher.node_type:
                    return False
            # For remove_node, old_value is a dict with "type" key
            elif mutation.type == "remove_node":
                if not isinstance(mutation.old_value, dict):
                    return False
                if mutation.old_value.get("type") != matcher.node_type:
                    return False
        return True

    return False
