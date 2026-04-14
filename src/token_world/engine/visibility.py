"""VisibilityProjector (D-14) — pure-function projection of graph state for an actor.

Closes GAP-CROSS01 (observation projection) and GAP-GRAPH04 (belief vs ground
truth). Output is a JSON-serializable dict[node_id, entry] consumed by the
Sonnet observer under a hard grounding constraint.

Composition (in order):
    1. Containment walk  — actor, location, contained neighbours, held items
    2. Illumination filter — dim rooms unless actor holds a light_source
    3. Property visibility — honour per-node ``hidden_properties``
    4. Belief overlay     — actor.beliefs overrides ground truth for already-projected nodes
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from token_world.graph import KnowledgeGraph

ILLUMINATION_THRESHOLD = 0.2  # rooms below this need light source to see details

# Edge types that indicate containment (room → object)
_CONTAINMENT_EDGE_TYPES = frozenset({"contains", "inside", "on"})


@dataclass(slots=True)
class VisibilityProjector:
    """Project graph state for one actor's observation (D-14).

    All operations are pure (read-only). No graph mutations are performed.

    Args:
        graph: The KnowledgeGraph to project from.
    """

    graph: KnowledgeGraph

    def project_for(
        self,
        actor_id: str,
        attention_state: dict | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Return a visibility projection for the given actor.

        Args:
            actor_id: The node ID of the actor to project for.
            attention_state: Optional attention modulation dict (D-12).
                ``{"suppress": [...], "boost": [...]}``
                When ``None`` (default) or empty dict, Stage 5 is skipped and
                the output is byte-for-byte identical to the pre-Phase-7 output
                (backward-compatible default).

        Returns:
            A dict mapping node_id → {type, properties, edges}.
            Empty dict if actor does not exist.
        """
        if not self.graph.has_node(actor_id):
            return {}

        projection: dict[str, dict[str, Any]] = {}

        # Stage 1: containment walk
        self._add_node(projection, actor_id)

        # Find actor's location (first 'location' edge)
        location_id = self._get_actor_location(actor_id)

        if location_id is not None and self.graph.has_node(location_id):
            self._add_node(projection, location_id)
            # Add nodes contained inside the location via containment edge types
            for contained in self._neighbors_by_edge_types(location_id, _CONTAINMENT_EDGE_TYPES):
                self._add_node(projection, contained)

        # Add held items (actor → item via 'holds' edge)
        for held in self._neighbors_by_edge_types(actor_id, frozenset({"holds"})):
            self._add_node(projection, held)

        # Stage 2: illumination filter
        projection = self._apply_illumination_filter(projection, actor_id, location_id)

        # Stage 3: property visibility classes
        projection = self._apply_hidden_properties(projection)

        # Stage 4: belief overlay
        projection = self._apply_belief_overlay(projection, actor_id)

        # Stage 5: attention modulation (D-12) — skipped when attention_state is falsy
        if attention_state:
            projection = self._apply_attention_state(projection, attention_state)

        return projection

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_node(self, projection: dict[str, dict[str, Any]], node_id: str) -> None:
        """Add a node entry to projection (skip if already present)."""
        if node_id in projection:
            return
        try:
            raw_props = self.graph.query(node_id)
        except KeyError:
            return
        node_type = raw_props.get("type", "entity")
        edges = self._outgoing_edges(node_id)
        projection[node_id] = {
            "type": node_type,
            "properties": dict(raw_props),  # defensive copy
            "edges": [{"type": e_type, "target": target} for e_type, target in edges],
        }

    def _get_actor_location(self, actor_id: str) -> str | None:
        """Return the first location target for actor_id, or None."""
        for e_type, target in self._outgoing_edges(actor_id):
            if e_type == "location":
                return target
        return None

    def _neighbors_by_edge_types(self, node_id: str, edge_types: frozenset[str]) -> list[str]:
        """Return target node IDs connected via any of the specified edge types."""
        return [target for e_type, target in self._outgoing_edges(node_id) if e_type in edge_types]

    def _outgoing_edges(self, node_id: str) -> list[tuple[str, str]]:
        """Return (edge_type, target_node_id) pairs for all outgoing edges.

        Uses ego_subgraph (public KnowledgeGraph API) to access edge properties
        without reaching into private NetworkX internals.
        """
        if not self.graph.has_node(node_id):
            return []
        try:
            subgraph = self.graph.ego_subgraph(node_id, depth=1, undirected=False)
        except nx.NodeNotFound:
            # has_node guard above should prevent this; treat as empty edges (TOCTOU safety)
            return []
        result = []
        for src, dst, edge_data in subgraph.edges(data=True):
            if src == node_id:  # only outgoing from node_id
                e_type = edge_data.get("type", "related") if edge_data else "related"
                result.append((str(e_type), dst))
        return result

    # ------------------------------------------------------------------
    # Stage 2: Illumination filter
    # ------------------------------------------------------------------

    def _apply_illumination_filter(
        self,
        projection: dict[str, dict[str, Any]],
        actor_id: str,
        location_id: str | None,
    ) -> dict[str, dict[str, Any]]:
        """Dim contained entities in dark rooms unless actor holds a light source."""
        if location_id is None or location_id not in projection:
            return projection

        room_entry = projection[location_id]
        illumination = room_entry["properties"].get("illumination", 1.0)
        if illumination >= ILLUMINATION_THRESHOLD:
            return projection

        # Check actor's held items for a light source
        actor_entry = projection.get(actor_id, {})
        for edge in actor_entry.get("edges", []):
            if edge["type"] != "holds":
                continue
            held_id = edge["target"]
            held_entry = projection.get(held_id, {})
            held_props = held_entry.get("properties", {})
            held_tags = held_props.get("tags", []) or []
            if "light_source" in held_tags or held_props.get("light_source") is True:
                # Actor has a light source — no dimming
                return projection

        # Identify contained nodes (connected to room via containment edge types)
        contained_ids: set[str] = {
            e["target"] for e in room_entry.get("edges", []) if e["type"] in _CONTAINMENT_EDGE_TYPES
        }

        # Rebuild projection with dimmed entries for contained nodes
        new_projection: dict[str, dict[str, Any]] = {}
        for node_id, entry in projection.items():
            if node_id == location_id:
                dimmed_entry = dict(entry)
                dimmed_entry["dimmed"] = True
                new_projection[node_id] = dimmed_entry
            elif node_id in contained_ids:
                new_projection[node_id] = {
                    "type": entry["type"],
                    "properties": {},
                    "edges": [],
                    "dimmed": True,
                }
            else:
                # Actor and held items are always fully visible
                new_projection[node_id] = entry

        return new_projection

    # ------------------------------------------------------------------
    # Stage 3: Property visibility classes
    # ------------------------------------------------------------------

    def _apply_hidden_properties(
        self, projection: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Remove properties named in each node's hidden_properties list."""
        new_projection: dict[str, dict[str, Any]] = {}
        for node_id, entry in projection.items():
            props = entry.get("properties", {})
            hidden_keys: list[str] = props.get("hidden_properties", []) or []
            if hidden_keys:
                blocked = set(hidden_keys) | {"hidden_properties"}
                filtered_props = {k: v for k, v in props.items() if k not in blocked}
                new_entry = dict(entry)
                new_entry["properties"] = filtered_props
                new_projection[node_id] = new_entry
            else:
                # Still remove hidden_properties key itself even if empty
                if "hidden_properties" in props:
                    new_entry = dict(entry)
                    new_entry["properties"] = {
                        k: v for k, v in props.items() if k != "hidden_properties"
                    }
                    new_projection[node_id] = new_entry
                else:
                    new_projection[node_id] = entry
        return new_projection

    # ------------------------------------------------------------------
    # Stage 5: Attention modulation (D-12)
    # ------------------------------------------------------------------

    def _apply_attention_state(
        self,
        projection: dict[str, dict[str, Any]],
        attention_state: dict,
    ) -> dict[str, dict[str, Any]]:
        """Stage 5 (D-12): suppress/boost properties based on attention_state.

        - suppress: list[str] — remove these property keys from every node's properties
        - boost:    list[str] — copy these property values (if present) to a new top-level
          ``attention_boosted`` key on each node; does NOT remove from properties

        Suppress is applied before boost (deterministic order). Unknown top-level keys in
        attention_state are silently ignored (forward-compat with future stages).

        Returns a new projection dict; neither the input projection nor attention_state
        is mutated (defensive-copy pattern consistent with other stages).
        """
        suppress = attention_state.get("suppress") or []
        boost = attention_state.get("boost") or []
        if not isinstance(suppress, list):
            suppress = []
        if not isinstance(boost, list):
            boost = []

        new_projection: dict[str, dict[str, Any]] = {}
        for node_id, entry in projection.items():
            props = dict(entry.get("properties", {}))  # defensive copy
            # Suppress first — removes keys entirely
            for key in suppress:
                props.pop(key, None)
            # Boost reads post-suppression props (so suppressed key yields no boost entry)
            boosted = {k: props[k] for k in boost if k in props}
            new_entry = dict(entry)
            new_entry["properties"] = props
            if boosted:
                new_entry["attention_boosted"] = boosted
            new_projection[node_id] = new_entry
        return new_projection

    # ------------------------------------------------------------------
    # Stage 4: Belief overlay
    # ------------------------------------------------------------------

    # Structural property keys that belief overlay MUST NOT override (Phase 5 IN-02
    # deferred fix, 2026-04-14). `type` classifies the node; `hidden_properties` is
    # the projector's own list; `beliefs` is the actor's belief dict itself and
    # allowing it would let one actor's beliefs recursively rewrite another's.
    # Everything else (location, subtype, named properties) remains override-able —
    # agents CAN believe a drink is a poison or a book is in another room.
    _BELIEF_STRUCTURAL_KEYS: frozenset[str] = frozenset({"type", "hidden_properties", "beliefs"})

    def _apply_belief_overlay(
        self,
        projection: dict[str, dict[str, Any]],
        actor_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Overlay actor's beliefs onto ground truth for already-projected nodes.

        Beliefs for nodes NOT in the projection are silently ignored (no phantoms).
        Structural property keys (`type`, `hidden_properties`, `beliefs`) are
        filtered out of each believed_props dict before merging — beliefs cannot
        override the projector's own bookkeeping or the node's classification.
        """
        actor_entry = projection.get(actor_id)
        if actor_entry is None:
            return projection

        beliefs = actor_entry.get("properties", {}).get("beliefs", {}) or {}
        if not isinstance(beliefs, dict) or not beliefs:
            return projection

        new_projection = dict(projection)
        for node_id, believed_props in beliefs.items():
            if node_id not in new_projection:
                continue  # no phantoms (GAP-GRAPH04)
            if not isinstance(believed_props, dict):
                continue  # silently ignore non-dict belief values
            # Strip structural keys — beliefs cannot override them (IN-02 fix)
            safe_believed_props = {
                k: v for k, v in believed_props.items() if k not in self._BELIEF_STRUCTURAL_KEYS
            }
            if not safe_believed_props:
                continue
            merged_entry = dict(new_projection[node_id])
            merged_props = dict(merged_entry.get("properties", {}))
            merged_props.update(safe_believed_props)
            merged_entry["properties"] = merged_props
            new_projection[node_id] = merged_entry

        return new_projection


# ---------------------------------------------------------------------------
# Module-level convenience alias
# ---------------------------------------------------------------------------


def project_for(
    graph: KnowledgeGraph,
    actor_id: str,
    attention_state: dict | None = None,
) -> dict[str, dict[str, Any]]:
    """Convenience function: create a projector and call project_for in one step."""
    return VisibilityProjector(graph).project_for(actor_id, attention_state)
