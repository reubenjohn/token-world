"""MechanicContext: DSL wrapper around KnowledgeGraph for mechanic execution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from token_world.graph import KnowledgeGraph, Mutation

if TYPE_CHECKING:
    # Imported only for type hints — avoids forcing rtree into the import
    # graph of mechanics that never touch spatial queries.
    from token_world.graph.spatial import SpatialIndex
    from token_world.graph.temporal import TemporalIndex


class MechanicContext:
    """DSL context provided to mechanics during check/apply.

    Wraps a :class:`KnowledgeGraph` and exposes query and mutation methods
    so that mechanics never access the graph directly.

    Attributes:
        actor: The agent (or entity) that initiated the action.
        target: The entity or location the action is directed at.
    """

    def __init__(self, graph: KnowledgeGraph, *, actor: str, target: str) -> None:
        self._graph = graph
        self.actor = actor
        self.target = target
        # Lazy: built on first access via the `spatial` property.
        self._spatial: SpatialIndex | None = None
        # Lazy: built on first access via the `temporal` property.
        self._temporal: TemporalIndex | None = None

    # --- Spatial (lazy R-tree index; GRAPH-06) ---

    @property
    def spatial(self) -> SpatialIndex:
        """Lazy R-tree spatial index over the graph.

        Constructed and populated on first access, then cached for the
        lifetime of this context. Mechanics that never access ``ctx.spatial``
        pay zero rtree cost — the import is deferred until this method runs.
        """
        if self._spatial is None:
            # Deferred import keeps rtree out of the module import graph for
            # mechanics that never need spatial queries.
            from token_world.graph.spatial import SpatialIndex

            self._spatial = SpatialIndex(self._graph)
            self._spatial.rebuild()
        return self._spatial

    # --- Temporal (lazy event-log query facade; GRAPH-07) ---

    @property
    def temporal(self) -> TemporalIndex:
        """Lazy temporal query facade over the graph event log.

        Constructed on first access, then cached for the lifetime of this
        context. Mechanics that never access ``ctx.temporal`` pay zero
        query cost — the import is deferred until this method runs.
        """
        if self._temporal is None:
            # Deferred import keeps the temporal module out of the import
            # graph for mechanics that never need history queries.
            from token_world.graph.temporal import TemporalIndex

            self._temporal = TemporalIndex(self._graph)
        return self._temporal

    # --- Query methods ---

    def query_node(self, node_id: str, property: str | None = None) -> Any:
        """Query a node's properties or a specific property value.

        Args:
            node_id: The node to query.
            property: Optional specific property to return.

        Returns:
            Dict of all properties, or the specific property value.
        """
        return self._graph.query(node_id, property)

    def query_neighbors(self, node_id: str) -> list[str]:
        """Get IDs of nodes adjacent to the given node.

        Args:
            node_id: The node whose neighbors to query.

        Returns:
            List of neighbor node IDs.
        """
        return self._graph.neighbors(node_id)

    def has_node(self, node_id: str) -> bool:
        """Check if a node exists in the graph."""
        return self._graph.has_node(node_id)

    def has_edge(self, src: str, dst: str) -> bool:
        """Check if a directed edge exists from src to dst."""
        return self._graph.has_edge(src, dst)

    def find_nodes(self, **filters: Any) -> list[str]:
        """Find nodes matching property filters.

        Args:
            **filters: Property name=value pairs to filter by.

        Returns:
            List of matching node IDs.
        """
        return self._graph.nodes(**filters)

    # --- Mutation methods ---

    def mutate(self, node_id: str, property: str, value: Any) -> Mutation:
        """Set a property on an existing node.

        Args:
            node_id: The node to modify.
            property: Property name.
            value: New value (must be JSON-serializable).

        Returns:
            A Mutation record describing the change.
        """
        return self._graph.set(node_id, property, value)

    def add_node(self, node_id: str, *, node_type: str, **props: Any) -> Mutation:
        """Add a new node to the graph.

        Args:
            node_id: Unique identifier for the node.
            node_type: Must be "agent" or "entity".
            **props: Arbitrary JSON-serializable properties.

        Returns:
            A Mutation record describing the change.
        """
        return self._graph.add_node(node_id, node_type=node_type, **props)

    def remove_node(self, node_id: str) -> Mutation:
        """Remove a node and all its edges.

        Args:
            node_id: The node to remove.

        Returns:
            A Mutation record describing the change.
        """
        return self._graph.remove_node(node_id)

    def add_edge(self, src: str, dst: str, **props: Any) -> Mutation:
        """Add a directed edge between two nodes.

        Args:
            src: Source node ID.
            dst: Destination node ID.
            **props: Arbitrary JSON-serializable edge properties.

        Returns:
            A Mutation record describing the change.
        """
        return self._graph.add_edge(src, dst, **props)

    def remove_edge(self, src: str, dst: str) -> Mutation:
        """Remove a directed edge.

        Args:
            src: Source node ID.
            dst: Destination node ID.

        Returns:
            A Mutation record describing the change.
        """
        return self._graph.remove_edge(src, dst)
