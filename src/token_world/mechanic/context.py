"""MechanicContext: DSL wrapper around KnowledgeGraph for mechanic execution."""

from __future__ import annotations

import hashlib
import random
from typing import TYPE_CHECKING, Any

from token_world.graph import KnowledgeGraph, Mutation

if TYPE_CHECKING:
    # Imported only for type hints — avoids forcing rtree into the import
    # graph of mechanics that never touch spatial queries.
    from token_world.graph.spatial import SpatialIndex
    from token_world.graph.temporal import TemporalIndex

    # CheckResult is used as return type for refuse(); runtime import is lazy
    # (inside the method body) to avoid the engine→mechanic→engine cycle.
    from token_world.mechanic.protocol import CheckResult


class MechanicContext:
    """DSL context provided to mechanics during check/apply.

    Wraps a :class:`KnowledgeGraph` and exposes query and mutation methods
    so that mechanics never access the graph directly.

    Attributes:
        actor: The agent (or entity) that initiated the action.
        target: The entity or location the action is directed at.
    """

    def __init__(
        self,
        graph: KnowledgeGraph,
        *,
        actor: str,
        target: str,
        tick_id: str | None = None,
        universe_seed: int | None = None,
    ) -> None:
        self._graph = graph
        self.actor = actor
        self.target = target
        self._tick_id = tick_id
        self._universe_seed = universe_seed
        # Lazy: built on first access via the `rng` property.
        self._rng: random.Random | None = None
        # Lazy: built on first access via the `spatial` property.
        self._spatial: SpatialIndex | None = None
        # Lazy: built on first access via the `temporal` property.
        self._temporal: TemporalIndex | None = None

    # --- Seeded RNG (D-19; lazy; derived from universe_seed + tick_id) ---

    @property
    def rng(self) -> random.Random:
        """Lazy seeded :class:`random.Random` for deterministic mechanic randomness.

        Derived from ``(universe_seed, tick_id)`` via BLAKE2b so two mechanics
        running in the same tick get identical sequences, while different ticks
        (or different universes) get distinct sequences.

        Raises:
            RuntimeError: if ``universe_seed`` or ``tick_id`` were not provided
                at construction time.
        """
        if self._rng is None:
            if self._universe_seed is None:
                raise RuntimeError(
                    "ctx.rng requires universe_seed to be set at MechanicContext construction"
                )
            if self._tick_id is None:
                raise RuntimeError(
                    "ctx.rng requires tick_id to be set at MechanicContext construction"
                )
            digest = hashlib.blake2b(
                f"{self._universe_seed}:{self._tick_id}".encode(),
                digest_size=8,
            ).digest()
            seed_int = int.from_bytes(digest, "big")
            self._rng = random.Random(seed_int)
        return self._rng

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

    def neighbors(self, node_id: str, *, relation: str | None = None) -> list[str]:
        """Get adjacent node IDs, optionally filtered by an edge ``relation``.

        Authoring-facing alias for :meth:`query_neighbors` that additionally
        supports an edge ``relation`` filter — the common case in seed
        mechanics (``ctx.neighbors(actor, relation="holds")``).

        Args:
            node_id: The node whose neighbors to query.
            relation: Optional edge ``relation`` property to filter by. When
                provided, only neighbors reached via an edge whose
                ``relation`` property equals this value are returned.

        Returns:
            List of neighbor node IDs.
        """
        if relation is None:
            return self._graph.neighbors(node_id)
        # Walk out-edges, keeping only those whose edge-data `relation`
        # matches. Uses the public ego_subgraph copy so we stay off the
        # private `_graph._graph` attribute (D-14 mutation-discipline
        # rationale applies symmetrically to reads).
        sub = self._graph.ego_subgraph(node_id, depth=1, undirected=False)
        out = []
        for nbr in sub.successors(node_id):
            data = sub.get_edge_data(node_id, nbr) or {}
            if data.get("relation") == relation:
                out.append(nbr)
        return out

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

    def set(self, node_id: str, property: str, value: Any) -> Mutation:
        """Authoring-facing alias for :meth:`mutate`.

        Mirrors the ``KnowledgeGraph.set`` name so mechanics can use whichever
        reads more naturally in context. Behaviour is identical to
        :meth:`mutate`.
        """
        return self._graph.set(node_id, property, value)

    def claim_id(self, name: str) -> str:
        """Claim a unique, human-readable node ID.

        Thin delegator to :meth:`KnowledgeGraph.claim_id`. Mechanics that
        create new nodes (e.g., ``craft``) should use this to deconflict IDs
        rather than hardcoding strings that may collide with operator-authored
        content.

        Args:
            name: The readable ID to claim (e.g., ``"sword"``). If taken,
                returns a suffixed variant (``"sword_a7"``).

        Returns:
            A unique ID safe to pass to :meth:`add_node`.
        """
        return self._graph.claim_id(name)

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

    # --- Refusal helper (D-13) ---

    def refuse(self, reason_code: str, details: dict[str, Any] | None = None) -> CheckResult:
        """Return a CheckResult(passed=False) with a standard refusal narrative (D-13).

        Mechanics call this inside ``check()`` when preconditions fail and they want
        consistent user-facing narrative. The narrative template lives in
        :mod:`token_world.engine.refusal`; we lazy-import to avoid a reverse dep.

        The rendered narrative is placed as the first element of ``reasons`` so it
        surfaces in observation synthesis and diagnostics.

        Args:
            reason_code: A known reason code (no_viable_action, no_such_target,
                low_confidence, mechanic_check_failed, conservation_violation,
                inventory_full, locked, blocked) or any arbitrary string.
            details: Template variables for the narrative (e.g. ``{"target": "gate"}``).

        Returns:
            :class:`~token_world.mechanic.protocol.CheckResult` with
            ``passed=False`` and the rendered narrative in ``reasons[0]``.
        """
        # Lazy import breaks the engine→mechanic→engine cycle (engine imports
        # Mechanic/MechanicContext; context lazy-imports RefusalTemplate).
        from token_world.engine.refusal import RefusalTemplate
        from token_world.mechanic.protocol import CheckResult

        narrative = RefusalTemplate.render(reason_code, details or {})
        return CheckResult(passed=False, reasons=[narrative])
