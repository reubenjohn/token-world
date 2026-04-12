"""Core KnowledgeGraph class wrapping NetworkX DiGraph."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import networkx as nx

from token_world.graph.events import EventStore, GraphEvent
from token_world.graph.identity import claim_id as _claim_id
from token_world.graph.models import ALLOWED_PROPERTY_TYPES, Mutation


def _validate_value(value: Any) -> None:
    """Validate that a property value is JSON-serializable.

    Raises:
        TypeError: If value is not an allowed type.
    """
    if not isinstance(value, ALLOWED_PROPERTY_TYPES):
        raise TypeError(
            f"Property value type {type(value).__name__} is not allowed. "
            f"Allowed types: str, int, float, bool, None, list, dict"
        )
    # Recursively validate containers
    if isinstance(value, list):
        for item in value:
            _validate_value(item)
    elif isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise TypeError(f"Dict keys must be strings, got {type(k).__name__}")
            _validate_value(v)


def _safe_copy(value: Any) -> Any:
    """Deep copy mutable values to prevent reference mutation."""
    if isinstance(value, (list, dict)):
        return copy.deepcopy(value)
    return value


class KnowledgeGraph:
    """Core knowledge graph for simulation state.

    All mutations are logged as events. The underlying NetworkX DiGraph
    should never be mutated directly outside this class.

    Args:
        db_path: Optional path to SQLite database for persistence.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()
        self._events: EventStore = EventStore()
        self._db_path = db_path
        self._current_tick: int = 0
        self._persistence: Any = None  # Set lazily if db_path provided

        if db_path is not None:
            # Import here to avoid circular imports; persistence is optional
            from token_world.graph.persistence import GraphPersistence

            self._persistence = GraphPersistence(db_path)

    # --- Tick management ---

    @property
    def current_tick(self) -> int:
        """Current simulation tick."""
        return self._current_tick

    def set_tick(self, tick_id: int) -> None:
        """Set the current tick for event logging."""
        self._current_tick = tick_id

    # --- Query API (read-only, no events) ---

    def query(self, node_id: str, property: str | None = None) -> Any:
        """Query a node's properties.

        Args:
            node_id: The node to query.
            property: Optional specific property to return. If None, returns
                all properties as a dict.

        Returns:
            Dict of all properties, or the specific property value.

        Raises:
            KeyError: If node_id does not exist.
        """
        if node_id not in self._graph:
            raise KeyError(f"Node '{node_id}' does not exist")
        if property is None:
            return dict(self._graph.nodes[node_id])
        return self._graph.nodes[node_id][property]

    def has_node(self, node_id: str) -> bool:
        """Check if a node exists."""
        return node_id in self._graph

    def has_edge(self, src: str, dst: str) -> bool:
        """Check if a directed edge exists from src to dst."""
        return self._graph.has_edge(src, dst)

    def neighbors(self, node_id: str) -> list[str]:
        """Get list of node IDs adjacent to the given node."""
        return list(self._graph.neighbors(node_id))

    def nodes(self, **filters: Any) -> list[str]:
        """Get node IDs, optionally filtered by property values.

        Args:
            **filters: Property name=value pairs to filter by.

        Returns:
            List of matching node IDs.
        """
        if not filters:
            return list(self._graph.nodes)
        result = []
        for node_id, data in self._graph.nodes(data=True):
            if all(data.get(k) == v for k, v in filters.items()):
                result.append(node_id)
        return result

    # --- Mutation API (logged as events) ---

    def add_node(self, node_id: str, *, node_type: str, **props: Any) -> Mutation:
        """Add a node to the graph.

        Args:
            node_id: Unique identifier for the node.
            node_type: Must be "agent" or "entity" (per D-01).
            **props: Arbitrary JSON-serializable properties.

        Returns:
            A Mutation record describing the change.

        Raises:
            ValueError: If node_type is not "agent" or "entity".
            TypeError: If any property value is not JSON-serializable.
        """
        if node_type not in ("agent", "entity"):
            raise ValueError(f"node_type must be 'agent' or 'entity', got '{node_type}'")
        # Validate all property values
        for v in props.values():
            _validate_value(v)

        # Deep copy mutable values
        safe_props = {k: _safe_copy(v) for k, v in props.items()}

        self._graph.add_node(node_id, type=node_type, **safe_props)

        new_value = {"type": node_type, **props}
        self._events.append(
            GraphEvent(
                tick_id=self._current_tick,
                event_type="add_node",
                target_id=node_id,
                property_name=None,
                old_value_json=None,
                new_value_json=json.dumps(new_value),
            )
        )
        return Mutation(
            type="add_node",
            target=node_id,
            property=None,
            old_value=None,
            new_value=new_value,
        )

    def add_edge(self, src: str, dst: str, **props: Any) -> Mutation:
        """Add a directed edge between two nodes.

        Args:
            src: Source node ID.
            dst: Destination node ID.
            **props: Arbitrary JSON-serializable edge properties.

        Returns:
            A Mutation record describing the change.

        Raises:
            TypeError: If any property value is not JSON-serializable.
        """
        for v in props.values():
            _validate_value(v)

        safe_props = {k: _safe_copy(v) for k, v in props.items()}
        self._graph.add_edge(src, dst, **safe_props)

        target = f"{src}->{dst}"
        self._events.append(
            GraphEvent(
                tick_id=self._current_tick,
                event_type="add_edge",
                target_id=target,
                property_name=None,
                old_value_json=None,
                new_value_json=json.dumps(props) if props else None,
            )
        )
        return Mutation(
            type="add_edge",
            target=target,
            property=None,
            old_value=None,
            new_value=props if props else None,
        )

    def set(self, node_id: str, property: str, value: Any) -> Mutation:
        """Set a property on an existing node.

        Args:
            node_id: The node to modify.
            property: Property name.
            value: New value (must be JSON-serializable).

        Returns:
            A Mutation record describing the change.

        Raises:
            KeyError: If node_id does not exist.
            TypeError: If value is not JSON-serializable.
        """
        if node_id not in self._graph:
            raise KeyError(f"Node '{node_id}' does not exist")
        _validate_value(value)

        old_value = self._graph.nodes[node_id].get(property)
        self._graph.nodes[node_id][property] = _safe_copy(value)

        self._events.append(
            GraphEvent(
                tick_id=self._current_tick,
                event_type="set_property",
                target_id=node_id,
                property_name=property,
                old_value_json=json.dumps(old_value) if old_value is not None else None,
                new_value_json=json.dumps(value),
            )
        )
        return Mutation(
            type="set_property",
            target=node_id,
            property=property,
            old_value=old_value,
            new_value=value,
        )

    def remove_node(self, node_id: str) -> Mutation:
        """Remove a node and all its edges.

        Args:
            node_id: The node to remove.

        Returns:
            A Mutation record describing the change.

        Raises:
            KeyError: If node_id does not exist.
        """
        if node_id not in self._graph:
            raise KeyError(f"Node '{node_id}' does not exist")
        old_data = dict(self._graph.nodes[node_id])
        self._graph.remove_node(node_id)

        self._events.append(
            GraphEvent(
                tick_id=self._current_tick,
                event_type="remove_node",
                target_id=node_id,
                property_name=None,
                old_value_json=json.dumps(old_data),
                new_value_json=None,
            )
        )
        return Mutation(
            type="remove_node",
            target=node_id,
            property=None,
            old_value=old_data,
            new_value=None,
        )

    def remove_edge(self, src: str, dst: str) -> Mutation:
        """Remove a directed edge.

        Args:
            src: Source node ID.
            dst: Destination node ID.

        Returns:
            A Mutation record describing the change.
        """
        old_data = dict(self._graph.edges[src, dst]) if self._graph.has_edge(src, dst) else None
        self._graph.remove_edge(src, dst)

        target = f"{src}->{dst}"
        self._events.append(
            GraphEvent(
                tick_id=self._current_tick,
                event_type="remove_edge",
                target_id=target,
                property_name=None,
                old_value_json=json.dumps(old_data) if old_data else None,
                new_value_json=None,
            )
        )
        return Mutation(
            type="remove_edge",
            target=target,
            property=None,
            old_value=old_data,
            new_value=None,
        )

    # --- Identity ---

    def claim_id(self, name: str) -> str:
        """Claim a human-readable node ID, deconflicting if needed.

        Args:
            name: Proposed node ID.

        Returns:
            The claimed ID (possibly with a hash suffix if name was taken).
        """
        return _claim_id(self._graph, name)

    # --- Persistence ---

    def save(self) -> None:
        """Persist graph state and events to SQLite.

        No-op if no db_path was provided.
        """
        if self._persistence is not None:
            self._persistence.save(self._graph, self._events.get_events(), self._current_tick)
            self._events.clear()

    def load(self) -> None:
        """Load graph state and events from SQLite.

        No-op if no db_path was provided or no data exists.
        """
        if self._persistence is not None and self._persistence.has_data():
            graph, events, tick = self._persistence.load()
            self._graph = graph
            self._events.set_events(events)
            self._current_tick = tick
